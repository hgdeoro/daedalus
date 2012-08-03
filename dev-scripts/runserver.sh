#!/bin/bash

#
# Starts the development server on port 64364.
#

set -e

$(dirname $0)/manage.sh runserver 64364
