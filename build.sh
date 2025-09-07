#!/usr/bin/env bash
set -o errexit  # stop on error

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate --noinput

# Collect static files for whitenoise
python manage.py collectstatic --noinput

