#!/bin/sh

# Log only a safe, non-sensitive summary of the DB engine (never log raw DSNs/credentials)
db_engine_summary=$(echo "${DATABASE_ENGINE:-$DATABASE}" | sed 's/.*\.//' | cut -c1-32)
echo "Database engine: ${db_engine_summary}"

# Check if wait-for-postgres is requested or if PostgreSQL is the active engine
if [ "$DATABASE" = "postgres" ] || echo "$DATABASE_ENGINE" | grep -iq "postgres"; then
    echo "Waiting for PostgreSQL at $DATABASES_HOST:$DATABASES_PORT..."

    # Loop until PostgreSQL is ready to accept connections or timeout is reached (60 seconds)
    timeout=60
    counter=0
    while ! nc -z "$DATABASES_HOST" "$DATABASES_PORT"; do
      sleep 0.5
      counter=$((counter + 1))
      if [ $counter -ge $((timeout * 2)) ]; then
        echo "ERROR: PostgreSQL at $DATABASES_HOST:$DATABASES_PORT did not become ready after $timeout seconds." >&2
        exit 1
      fi
    done

    echo "PostgreSQL started"
fi

if [ -z "$DJANGO_SETTINGS_MODULE" ]; then
    echo "ERROR: DJANGO_SETTINGS_MODULE is not set."
    exit 1
fi

# Run migrations if explicitly enabled or if running in development context
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
else
    echo "Skipping database migrations (RUN_MIGRATIONS != true)."
fi

# Collect static files if explicitly enabled or if running in development context
if [ "$RUN_COLLECTSTATIC" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
else
    echo "Skipping collectstatic (RUN_COLLECTSTATIC != true)."
fi

# Execute the command passed as arguments to the entrypoint script
exec "$@"

