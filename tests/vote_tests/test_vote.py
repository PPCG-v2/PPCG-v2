from app.models.PostVote import PostVote
from app.models.AnswerVote import AnswerVote
from app.models.User import User
from app.models.Post import Post
from app.models.Answer import Answer
from app.controllers import vote
from tests.test_base import TestBase
from flask import g
import json


# noinspection PyUnresolvedReferences
import app.routes.post
# noinspection PyUnresolvedReferences
import app.routes.answer
# noinspection PyUnresolvedReferences
import app.routes.vote


class TestVote(TestBase.TestDB, TestBase.TestFlask):
    def setUp(self):
        super().setUp()

        self.user = User(name='Test User', email='test@user.com')
        self.session.add(self.user)
        g.user = self.user

        self.post = Post(title='Testing Votes API', body='Testing Votes API', user_id=self.user.id)
        self.session.add(self.post)

        self.answer = Answer(post_id=self.post.id, user_id=self.user.id)
        self.session.add(self.answer)

        vote.do_post_vote(self.post_id, 1)
        vote.do_answer_vote(self.answer.id, -1)

        self.session.commit()

    def test_post_vote_get(self):
        result = self.app.get(f"/post/{self.post.id}/vote")
        self.assertEqual(result.status_code, 200)

        data = json.loads(result.data)
        self.assertEqual(data['vote'], 1)
        self.assertEqual(data['user'], self.user.id)
        self.assertEqual(data['post'], self.post.id)

    def test_answer_vote_get(self):
        result = self.app.get(f"/answer/{self.answer.id}/vote")
        self.assertEqual(result.status_code, 200)

        data = json.loads(result.data)
        self.assertEqual(data['vote'], -1)
        self.assertEqual(data['user'], self.user.id)
        self.assertEqual(data['answer'], self.answer.id)

    def test_post_vote_change(self):
        post_result = self.app.post(f"/post/{self.post.id}/vote", data={'vote': 0})
        self.assertEqual(post_result.status_code, 200)

        get_result = self.app.get(f"/post/{self.post.id}/vote")
        self.assertEqual(get_result.status_code, 200)
        data = json.loads(get_result.data)
        self.assertEqual(data['vote'], 0)

        post_vote = PostVote.query.filter_by(post_id=self.post.id, user_id=self.user.id).first()
        self.session.expire(post_vote)

    def test_answer_vote_change(self):
        post_result = self.app.post(f"/answer/{self.answer.id}/vote", data={'vote': 0})
        self.assertEqual(post_result.status_code, 200)

        get_result = self.app.get(f"/answer/{self.answer.id}/vote")
        self.assertEqual(get_result.status_code, 200)
        data = json.loads(get_result.data)
        self.assertEqual(data['vote'], 0)

        answer_vote = AnswerVote.query.filter_by(answer_id=self.answer.id, user_id=self.user.id).first()
        self.session.expire(answer_vote)

    def test_post_vote_total(self):
        result = self.app.get(f"/post/{self.post.id}/votes")
        self.assertEqual(result.status_code, 200)

        data = json.loads(result.data)
        self.assertEqual(data['votes'], 1)

    def test_post_vote_total(self):
        result = self.app.get(f"/answer/{self.answer.id}/votes")
        self.assertEqual(result.status_code, 200)

        data = json.loads(result.data)
        self.assertEqual(data['votes'], -1)
