#!/bin/bash

# Exit on any error
set -e

echo "Starting Django application setup..."

# Wait for database to be ready (optional but recommended)
echo "Waiting for database..."
python manage.py wait_for_db 2>/dev/null || echo "wait_for_db command not available, proceeding..."

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create countries data
echo "Creating countries..."
python manage.py create_countries

# Create currencies data
#echo "Creating currencies..."
#python manage.py create_currencies

# Start the Django development server
echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000
