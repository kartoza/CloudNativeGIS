# coding=utf-8
"""Context Layer Management."""

from django.contrib.auth import get_user_model
from django.test.client import Client, MULTIPART_CONTENT

User = get_user_model()


class BaseTest:
    """Base of test."""

    JSON_CONTENT = 'application/json'
    password = 'password'

    def assertRequestGetView(self, url, code, user=None):
        """Assert request GET view with code."""
        client = Client()
        if user:
            client.login(username=user.username, password=self.password)
        response = client.get(url)
        self.assertEqual(response.status_code, code)
        return response

    def assertRequestPostView(
            self, url, code, data, user=None, content_type=MULTIPART_CONTENT
    ):
        """Assert request POST view with code."""
        client = Client()
        if user:
            client.login(username=user.username, password=self.password)
        response = client.post(url, data=data, content_type=content_type)
        self.assertEqual(response.status_code, code)
        return response

    def assertRequestPutView(
            self, url, code, data, user=None, content_type=MULTIPART_CONTENT
    ):
        """Assert request POST view with code."""
        client = Client()
        if user:
            client.login(username=user.username, password=self.password)
        response = client.put(url, data=data, content_type=content_type)
        self.assertEqual(response.status_code, code)
        return response

    def assertRequestPatchView(
            self, url, code, data, user=None, content_type=MULTIPART_CONTENT
    ):
        """Assert request POST view with code."""
        client = Client()
        if user:
            client.login(username=user.username, password=self.password)
        response = client.patch(url, data=data, content_type=content_type)
        self.assertEqual(response.status_code, code)
        return response

    def assertRequestDeleteView(
            self, url, code, user=None, data=None,
            content_type="application/json"
    ):
        """Assert request DELETE view with code."""
        client = Client()
        if user:
            client.login(username=user.username, password=self.password)
        response = client.delete(url, data=data, content_type=content_type)
        self.assertEqual(response.status_code, code)
        return response
