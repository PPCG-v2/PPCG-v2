from app.server import server
from app.notifications.webapn import supports_web_apn, create_pushpackage_zip
from app.controllers import push_notifications
from app.helpers.render import render_json
from app.models.PushNotificationDevice import PushNotificationDevice, PNProvider
from app.session.csrf import csrf_protected
from app.models.User import User
from config import notifications

from flask import abort, request, session, g, send_file
from json import dumps as json_dumps

import bugsnag

webapn_redis_id_prefix = 'webapn:'
webapn_redis_id_time = 60 * 2 # In seconds

"""
Safari Push Notification routes.

Because Apple likes to be special we have to make
seperate things to integrate with Web APN. Very important
to have caching enabled if doing APN because otherwise
this will be re-preparing the APN every time.
"""

@server.route("/webapn/get_identification", methods=['POST'])
@csrf_protected
def webapn_get_identification():
    if not isinstance(g.user, User):
        return abort(401)

    # Generate a short-term expiring token
    authorization_token = push_notifications.generate_temporary_id()

    return render_json({'token': authorization_token})

@server.route("/static/webapn/v<int:version>/pushPackages/<web_apn_id>", methods=['POST'])
def webapn_get_push_package(version, web_apn_id):
    if not supports_web_apn(web_apn_id) or not push_notifications.is_valid_webapn_version(version):
        return abort(404)

    # Validate authorization token (associated with user)
    json = request.get_json(silent=True)
    authorization_token = json.get('token', None)

    if authorization_token is None:
        return abort(401)

    # Get the user behind the temporary token
    user = push_notifications.get_temporary_id_user(authorization_token)

    if not isinstance(user, User):
        return abort(403)

    # Now we create a 'device' this represents PNs for one device
    # this includes an 'auth token' which is a secure association
    # between the device and the authorized user
    device = push_notifications.add_push_notification_device(user=user, provider=PNProvider.WEB_APN)

    # Create the pushpackage with all this data
    pushpackage = create_pushpackage_zip(device=device)

    return send_file(pushpackage, attachment_filename='Axtell.pushpackage', as_attachment=True)

@server.route("/static/webapn/v<int:version>/devices/<device_token>/registrations/<web_apn_id>", methods=['POST'])
def webapn_add_registration(version, device_token, web_apn_id):
    if not supports_web_apn(web_apn_id) or not push_notifications.is_valid_webapn_version(version):
        return abort(404)

    authorization_header = request.headers.get('Authorization', None)
    if authorization_header is None:
        return abort(401)

    authorization_header = authorization_header.strip()

    if not authorization_header.startswith('ApplePushNotifications'):
        return abort(400)

    authorization_token = authorization_header[len('ApplePushNotifications '):]

    # 36 is the length of the UUID
    if len(authorization_token) != 36:
        return abort(400)

    device = push_notifications.\
        set_push_notification_device(
            authorization_token=authorization_token,
            provider=PNProvider.WEB_APN,
            device_token=device_token
        )

    if not isinstance(device, PushNotificationDevice):
        return abort(403)

    return ('OK', 200)

@server.route("/static/webapn/v<int:version>/devices/<device_token>/registrations/<web_apn_id>", methods=['DELETE'])
def webapn_delete_registration(version, device_token, web_apn_id):
    if not supports_web_apn(web_apn_id) or not push_notifications.is_valid_webapn_version(version):
        return abort(404)

    authorization_header = request.headers.get('Authorization', None)
    if authorization_header is None:
        return abort(401)

    authorization_header = authorization_header.strip()

    if not authorization_header.startswith('ApplePushNotifications'):
        return abort(400)

    authorization_token = authorization_header[len('ApplePushNotifications '):]
    # 36 is the length of the UUID
    if len(authorization_token) != 36:
        return abort(400)

    did_delete = push_notifications.\
        delete_push_notification_device(
            authorization_token=authorization_token,
            provider=PNProvider.WEB_APN
        )

    if not did_delete:
        return abort(400)

    return ('OK', 200)

@server.route("/static/webapn/v<int:version>/log", methods=['POST'])
def webapn_log(version):
    if not push_notifications.is_valid_webapn_version(version):
        return abort(404)

    logs = request.get_json(silent=True)["logs"]

    if server.debug:
        print(json_dumps(logs))

    if bugsnag.configuration.api_key is not None:
        bugsnag.notify(
            Exception("WebAPN exception"),
            meta_data={"webapn_logs": {f"Log {i}": log for i, log in enumerate(logs)}}
        )

    return ('', 204)