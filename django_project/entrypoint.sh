#!/bin/sh

# Exit script in case of error
set -e

echo $"\n\n\n"
echo "-----------------------------------------------------"
echo "STARTING DJANGO ENTRYPOINT $(date)"
echo "-----------------------------------------------------"

# Run NPM
#cd /home/web/django_project/frontend
#echo "npm install"
#npm install --verbose
#echo "npm build"
#npm run build

# Run initialization
cd /home/web/django_project
echo 'Running initialize.py...'
python -u initialize.py
python manage.py migrate

echo "-----------------------------------------------------"
echo "FINISHED DJANGO ENTRYPOINT --------------------------"
echo "-----------------------------------------------------"

# Run the CMD
exec "$@"