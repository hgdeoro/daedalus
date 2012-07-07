#!/bin/bash

#
# Run the manage.py / django-admin.py of Daedalus with backend enabled.
#

set -e

export DJANGO_SETTINGS_MODULE="hgdeoro.daedalus.web.settings_backend_only"

cd $(dirname $0)

./manage.sh $*

