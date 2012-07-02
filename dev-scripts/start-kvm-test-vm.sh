#!/bin/bash

[ "$UID" -eq 0 ] || { echo "ERROR: must be ran as root." ; exit 1 ; }

set -e
set -u

DAEDALUS_VM_NAME="vm.centos-6-daedalus-tests"

virsh list | awk '{ print $2; }' | egrep -q "^${DAEDALUS_VM_NAME}$" || {
	virsh start $DAEDALUS_VM_NAME
}

for i in $(seq 1 180) ; do
	echo "Sending ping..."
	ping -w 1 -c 1 $DAEDALUS_VM_NAME > /dev/null 2> /dev/null || {
		continue
	}
	echo "OK"
	exit
done

