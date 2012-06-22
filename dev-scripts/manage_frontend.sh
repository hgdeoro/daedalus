#!/bin/bash

#
# Run the manage.py / django-admin.py of Daedalus with frontend enabled.
#

set -e

cd $(dirname $0)/..

# path
export PYTHONPATH=src

# virtualenv
. ./virtualenv/bin/activate

export DJANGO_SETTINGS_MODULE="hgdeoro.daedalus.web.settings_frontend_only"

django-admin.py $*

