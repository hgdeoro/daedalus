#!/bin/bash

#
# Run the tests of frontend and backend.
#

set -e

if [ -z "$1" ] ; then
	$(dirname $0)/manage.sh test --liveserver=localhost:65101 frontend backend
else
	$(dirname $0)/manage.sh test --liveserver=localhost:65101 $*
fi
