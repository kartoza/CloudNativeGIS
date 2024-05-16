# coding=utf-8

import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserF(factory.django.DjangoModelFactory):
    """Factory for User."""

    username = factory.Sequence(lambda n: 'user_{}'.format(n))
    password = factory.PostGenerationMethodCall('set_password', 'password')

    class Meta:  # noqa: D106
        model = User


def create_user(**kwargs):
    """Create user with role."""
    return UserF(**kwargs)
