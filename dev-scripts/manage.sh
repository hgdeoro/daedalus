#!/bin/bash

#
# Run the manage.py / django-admin.py of Daedalus with both frontend and backend enabled.
#

set -e

cd $(dirname $0)/..

# path
export PYTHONPATH=src

# virtualenv
. ./virtualenv/bin/activate

export DJANGO_SETTINGS_MODULE="hgdeoro.daedalus.settings"

django-admin.py $*

