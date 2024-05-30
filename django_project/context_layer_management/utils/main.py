# coding=utf-8
"""Context Layer Management."""

import os
import random
import string

# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    ))


def ABS_PATH(*args):
    """Return absolute path of django project."""
    return os.path.join(DJANGO_ROOT, *args)


def id_generator(size=12, chars=string.ascii_uppercase + string.digits):
    """Return a random string of specified size."""
    return ''.join(random.choice(chars) for _ in range(size))
