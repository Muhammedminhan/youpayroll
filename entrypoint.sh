#!/bin/sh

# Log only the database type safely (never log connection string or credentials)
db_to_check="${DATABASE_ENGINE:-$DATABASE}"
case "$db_to_check" in
  *postgres*|*postgresql*)
    echo "Database engine: PostgreSQL"
    ;;
  *mysql*)
    echo "Database engine: MySQL"
    ;;
  *sqlite*)
    echo "Database engine: SQLite"
    ;;
  *)
    echo "Database engine: configured"
    ;;
esac


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

# Run migrations only when explicitly enabled.
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
else
    echo "Skipping database migrations (RUN_MIGRATIONS != true)."
fi

# Collect static files only when explicitly enabled.
if [ "$RUN_COLLECTSTATIC" = "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
else
    echo "Skipping collectstatic (RUN_COLLECTSTATIC != true)."
fi

# Execute the command passed as arguments to the entrypoint script
exec "$@"
