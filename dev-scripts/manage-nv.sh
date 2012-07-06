#!/bin/bash

#
# Run Django's manage / django-admin script, WITHOUT using virtualenv
#

set -e

export PYTHONPATH="$( cd $(dirname $0) ; pwd )/../src:$PYTHONPATH"
export DJANGO_SETTINGS_MODULE="hgdeoro.daedalus.settings"

if [ "$(which django-admin.py)" ] ; then
	django-admin.py $*
elif [ "$(which django-admin)" ] ; then
	django-admin $*
else
	echo "ERROR: couldn't locate django-admin nor django-admin.py"
	exit 1
fi

