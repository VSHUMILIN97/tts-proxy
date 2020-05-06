#!/bin/sh

echo "Waiting for postgres..."

while ! netcat -z $PSQL_HOST $PSQL_PORT; do
  sleep 0.1
done

echo "PostgreSQL started"


python manage.py migrate
python manage.py collectstatic --no-input --clear

exec "$@"