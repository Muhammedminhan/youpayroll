#!/bin/sh

# Print the value of the DATABASE environment variable
echo "$DATABASE"

# Check if wait-for-postgres is requested or if PostgreSQL is the active engine
if [ "$DATABASE" = "postgres" ] || echo "$DATABASE_ENGINE" | grep -iq "postgres"; then
    echo "Waiting for postgres..."

    # Loop until PostgreSQL is ready to accept connections (using nc -z from netcat-openbsd)
    while ! nc -z "$DATABASES_HOST" "$DATABASES_PORT"; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

if [ -z "$DJANGO_SETTINGS_MODULE" ]; then
    echo "ERROR: DJANGO_SETTINGS_MODULE is not set."
    exit 1
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Execute the command passed as arguments to the entrypoint script
exec "$@"

