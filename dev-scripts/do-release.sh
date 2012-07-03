#!/bin/bash

set -e

cd $(dirname $0)/..

[ $(git status --short --untracked-files=no | wc -l) -gt 0 ] && {
	echo ""
	echo "WARN: the working directory has uncommited changes"
	echo ""
	echo "Press ENTER to continue..."
	read
}

echo ./virtualenv/bin/python setup.py --version | grep -q 'dev' && {
	echo ""
	echo "WARN: Version information does NOT contains 'dev'"
	echo ""
	echo "Press ENTER to continue..."
	read
}

if [ -z "$DONTTEST" ] ; then

	echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
	echo " Running tests (set DONTTEST to skip this)"
	echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

	./dev-scripts/test.sh

fi

echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo " Remove '-dev' from setup.py. Press ENTER to edit setup.py"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
read

vim setup.py

export VER="$(./virtualenv/bin/python setup.py --version)"

echo "Version: $VER"

echo $VER | grep -q 'dev' && {
	echo "ERROR: Version information contains 'dev'"
	exit 1
}

git commit setup.py -m "Updated setup: version=v$VER"

git tag -a -m "Version $VER" "v$VER"

git tag -f stable

git archive --format=tar --prefix=daedalus-$VER/ stable | gzip > daedalus-$VER.tgz

echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo " Increment version and add '-dev' to setup.py. Press ENTER to edit setup.py"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
read

vim setup.py

NEWVER="$(./virtualenv/bin/python setup.py --version)"

if [ "$VER" = "$NEWVER" ] ; then
	echo "WARN: you hasn't changed version on setup.py!"
else
	git commit setup.py -m "Updated setup: version=v$NEWVER"
fi

echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo " Press ENTER to do the push"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
read

git push
git push --tags

