#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Poblar base de datos (Ejecuta una sola vez gracias a los guards internos)
python populate_db.py
