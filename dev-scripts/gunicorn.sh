#!/bin/bash

set -e

cd $(dirname $0)/..

# path
export PYTHONPATH=src

# virtualenv
. ./virtualenv/bin/activate

export DJANGO_SETTINGS_MODULE="hgdeoro.daedalus.settings"

gunicorn --bind=0.0.0.0:8084 hgdeoro.daedalus.web.wsgi:application $*

