#!/bin/bash

#
# Run the manage.py / django-admin.py of Daedalus with both frontend and backend enabled.
#
# This scripts automatically 'activates' the virtualenv.
# If you don't use virtualenv, and all the requisites are installed elsewhere (and
# accesible by Python), you could use 'manage-nv.sh' (manage-non-virtualenv).
#

set -e

cd $(dirname $0)/..

# path
export PYTHONPATH=src

# virtualenv
. ./virtualenv/bin/activate

export DJANGO_SETTINGS_MODULE="hgdeoro.daedalus.settings"

django-admin.py $*

