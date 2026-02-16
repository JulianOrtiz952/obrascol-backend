#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python3 manage.py collectstatic --no-input
python3 manage.py migrate

# Poblar base de datos (Ejecuta una sola vez gracias a los guards internos)
python3 -u populate_db.py
