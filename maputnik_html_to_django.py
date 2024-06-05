import re


def maputnik_html_to_django():
    """Change hmtl file to django file."""
    path = 'django_project/cloud_native_gis/maputnik/index.html'

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
        filedata = filedata.replace('/maputnik', '')

    with open(path, 'w') as file:
        file.write(filedata)


maputnik_html_to_django()
