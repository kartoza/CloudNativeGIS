# coding=utf-8
"""Context Layer Management."""

import os

# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    ))


def ABS_PATH(*args):
    """Return absolute path of django project."""
    return os.path.join(DJANGO_ROOT, *args)
