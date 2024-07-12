"""
Cloud Native GIS.

.. note:: Script for changing html to django templates.
"""
import os
import re
import shutil


def maputnik_html_to_django():
    """Change hmtl file to django file."""
    folder = 'django_project/cloud_native_gis/templates/'
    path = os.path.join(folder, 'cloud_native_gis/index.html')

    with open(path, 'r') as file:
        filedata = file.read()
        if '{% load static %}' not in filedata:
            filedata = '{% load static %}\n' + filedata
        filedata = re.sub(
            r'crossorigin src="([^"]*)"',
            r'crossorigin src="{% static "\1" %}"',
            filedata
        )
        filedata = re.sub(
            r'href="([^"]*)"',
            r'href="{% static "\1" %}"',
            filedata
        )
        filedata = filedata.replace('/maputnik/static/', '')
        filedata = filedata.replace('/static/static/', '')
        filedata = filedata.replace(
            '</head>',
            '''
              <script>
                window.csrfmiddlewaretoken = '{{ csrf_token }}';
              </script>'''
        )

    with open(path, 'w') as file:
        file.write(filedata)

    # Move static file
    static_folder = os.path.join(
        folder, 'cloud_native_gis', 'static', 'cloud_native_gis'
    )
    shutil.rmtree(
        'django_project/cloud_native_gis/static/cloud_native_gis',
        ignore_errors=True
    )
    shutil.move(static_folder, 'django_project/cloud_native_gis/static')
    shutil.move(
        path, os.path.join(folder, 'cloud_native_gis/maputnik.html')
    )


maputnik_html_to_django()
