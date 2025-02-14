"""
Cloud Native GIS.

.. note:: Application setup.
"""
# !/usr/bin/env python

import io

from setuptools import setup, find_packages

__version__ = io.open('django_project/version.txt', encoding='utf-8').read()

setup(
    name='Cloud Native GIS',
    version=__version__,
    author='Irwan Fathurrahman',
    author_email='irwan@kartoza.com',
    packages=find_packages(
        where='django_project',
        include=['cloud_native_gis*'],
    ),
    package_dir={'': 'django_project'},
    scripts=[],
    url='https://github.com/kartoza/CloudNativeGIS',
    license='MIT',
    description=(
        'Django application to manage context layer.'
    ),
    include_package_data=True,
    long_description=io.open('README.md', encoding='utf-8').read(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Framework :: Django :: 4.2',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    install_requires=[
        'Django >= 3.2.16',
        'djangorestframework >= 3.14.0',
        'djangorestframework-gis >= 1.0',
        'django-cors-headers==4.3.1',
        'GeoAlchemy2 >= 0.15.1',
        'geopandas >= 0.13.2',
        'fiona==1.10.1'
    ],
)
