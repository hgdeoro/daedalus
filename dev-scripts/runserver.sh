#!/bin/bash

#
# Starts the development server on port 8084.
#

set -e

$(dirname $0)/manage.sh runserver 8084

