#!/bin/bash

set -ex

export SERVER_NAME=${SERVER_NAME:-$(hostname --fqdn)}

# Wait for Database
/wait-for-it.sh database:5432 -t 60

# Clear runtime contexts
rm -rf /var/run/apache2/* /tmp/apache2*

APP_DIRECTORY="/dataserver"

# Make sure the local directory is a Python package
if [ ! -f ${APP_DIRECTORY}/local/__init__.py ]; then
    touch ${APP_DIRECTORY}/local/__init__.py
fi

# Modify the 'www-data' user (Debian)
if [ -z "$APACHE_UID" ]; then
    echo "Default Apache UID will be used!"
else
    usermod --non-unique --uid "${APACHE_UID}" www-data
fi

# check of database exists and initialize it if not
for trial in {1..5}; do
    echo "Migrating database tables ... (attempt $trial)"
    /venv/bin/python3 ${APP_DIRECTORY}/manage.py migrate --noinput && break
    sleep 5
done

# Initialize Cache Directory
if [ ! -f "/cache/.init" ]; then
    # Update ownership to 'www-data' (Debian)
    chown -R www-data:www-data /cache
    touch /cache/.init
fi

# Launch Debian's apache2 binary using its standard environment variables
# Debian's Apache requires variables like APACHE_RUN_DIR to be sourced first.
source /etc/apache2/envvars
exec /usr/sbin/apache2 -DFOREGROUND -e debug
