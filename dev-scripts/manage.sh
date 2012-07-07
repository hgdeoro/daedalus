#!/bin/bash

#
# Run the manage.py / django-admin.py of Daedalus with both frontend and backend enabled.
#
# This scripts automatically 'activates' the virtualenv (if it exists).
# If you don't use virtualenv, and all the requisites shoud be installed elsewhere (and
# accesible by Python).
#

set -e

cd $(dirname $0)/..

# path
export PYTHONPATH="src:$PYTHONPATH"

# check if virtualenv exists and activate it
if [ -d ./virtualenv ] ; then
	. ./virtualenv/bin/activate
fi

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"hgdeoro.daedalus.settings"}

if [ "$(which django-admin.py)" ] ; then
        django-admin.py $*
elif [ "$(which django-admin)" ] ; then
        django-admin $*
else
        echo "ERROR: couldn't locate django-admin nor django-admin.py"
        exit 1
fi

