#!/bin/bash

# This script is used to build and set up the Django project.

# Install MySQL development library
apt-get install -y libmysqlclient-dev

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install project dependencies
if ! python -m pip install -r requirements.txt; then
  echo "Error: Failed to install dependencies."
  exit 1
fi

# Make database migrations
if ! python manage.py makemigrations core; then
  echo "Error: Failed to make migrations for core app."
  exit 1
fi

if ! python manage.py makemigrations users; then
  echo "Error: Failed to make migrations for users app."
  exit 1
fi

if ! python manage.py migrate; then
  echo "Error: Failed to apply migrations."
  exit 1
fi
