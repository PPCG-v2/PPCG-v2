#!/usr/bin/env bash
set -e

# Ensure correct directory
cd /var/www/ppcg-v2

echo "REMOTE DEPLOY: UPDATING GIT"
echo "HEAD initially at version:"
echo "$(git rev-parse @)"

git fetch origin
git reset --hard origin/master

echo "Deployed to version:"
echo "$(git rev-parse @)"

# Ensure webasset dirs exist
mkdir -p static/css
chmod 755 static/css
chmod g+s static/css

mkdir -p static/lib
chmod 755 static/lib
chmod g+s static/lib

# Update python packages

echo "REMOTE DEPLOY: UPDATING PYTHON PACKAGES"
source venv/bin/activate
pip3 install -r requirements.txt

echo "REMOTE DEPLOY: UPDATING NPM PACKAGES"
npm install --production
npm update caniuse-lite browserslist

echo "REMOTE DEPLOY: ALEMBIC UPGRADES"
PYTHONPATH=$PYTHONPATH:/var/www/ppcg-v2 alembic revision --autogenerate -m "$(git log --format=%B -n 1)"
PYTHONPATH=$PYTHONPATH:/var/www/ppcg-v2 alembic upgrade head

echo "REMOTE DEPLOY: CLEANING OLD JAVASCRIPT"
rm -rf static/lib/*

echo "REMOTE DEPLOY: STOPPING SERVICE"
sudo service ppcg-v2 stop

echo "REMOTE DEPLOY: KILLING CELERY"
sudo -E env "PATH=$PATH" celery multi stop w1 -A celery_server --logfile=w1.log --pidfile=w1.pid
if [ -e beat.pid ]
then
  echo "REMOTE DEPLOY: KILLING CELERY BEAT";
  sudo kill $( cat beat.pid );
  echo "REMOTE DEPLOY: REMOVING beat.pid";
  sudo rm beat.pid;
fi

echo "REMOTE DEPLOY: CELERY PURGE"
sudo -E env "PATH=$PATH" celery purge -f -A celery_server

echo "REMOTE DEPLOY: STARTING CELERY"
sudo -E env "PATH=$PATH" celery multi start w1 -A celery_server --logfile=w1.log --pidfile=w1.pid --loglevel=DEBUG

echo "REMOTE DEPLOY: STARTING SERVICE"
sudo service ppcg-v2 start

# echo "REMOTE DEPLOY: STARTING CELERY BEAT SERVER"
# celery beat -A celery_server --pidfile=beat.pid --logfile=beat.log --loglevel=DEBUG --detach
