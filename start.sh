#!/usr/bin/env bash
# start.sh
# exit on error
set -o errexit

echo "Applying database migrations..."
python3 manage.py migrate

echo "Populating the database..."
python3 manage.py populate_polvorin

echo "Starting server..."
gunicorn core.wsgi -b 0.0.0.0:8000
