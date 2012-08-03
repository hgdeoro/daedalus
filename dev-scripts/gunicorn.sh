#!/bin/bash

set -e

cd $(dirname $0)/..

# path
export PYTHONPATH="src:src-client:$PYTHONPATH"

# check if virtualenv exists and activate it
if [ -d ./virtualenv ] ; then
        . ./virtualenv/bin/activate
fi

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"daedalus.settings"}

gunicorn --bind=0.0.0.0:64364 daedalus.wsgi:application $*

