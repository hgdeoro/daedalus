#!/bin/bash

echo "#"
echo "# Creates randoms messages in the 'production' keyspace."
echo "# This is used to populate the Cassandra keyspace with random log messages"
echo "# to develop and test the frontend."
echo "#"
echo "# The messages are inserted directly to Cassandra (without using the backend)"
echo "#"
echo "# This runs until Ctrl+C is pressed."
echo "#"

set -e

export dont_drop_daedalus_tests=1

$(dirname $0)/test.sh backend.BulkSave.bulk_save_multimsg

