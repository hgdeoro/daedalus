#!/bin/bash

#
# Run the manage.py / django-admin.py of Daedalus with frontend enabled.
#

set -e

cd $(dirname $0)

export DJANGO_SETTINGS_MODULE="daedalus.settings_frontend_only"

./manage.sh $*

