#!/bin/sh
echo "Waiting for postgres..."

while ! nc -z $PSQL_HOST $PSQL_PORT; do
  sleep 0.1
done

echo "PostgreSQL started"

export DEBUG_MODE=1
python manage.py migrate
python manage.py collectstatic --no-input --clear

exec "$@"
