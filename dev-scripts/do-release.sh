#!/bin/bash

#
#
# Script to release a new stable version of Daedalus (server and python client).
#
# Based on the instruction that 'evolved' on setup.py, now the script
#  automatically handles version number modification.
#
#
#  + run tests
#  + remove '-dev' from version of daedalus_version.py
#  + git commit daedalus_version.py -m "Updated daedalus_version: version=v$(python daedalus_version.py)"
#  + git tag -a -m "Version $(python daedalus_version.py)" "v$(python daedalus_version.py)"
#  + git tag -f stable
#  + python setup.py sdist upload
#  - [client]  increment version number at `src-client/setup.py`
#  - [client]  cd src-client ; python setup.py sdist upload ; cd ..
#  + increment version number and add '-dev' on version of daedalus_version.py
#  + git push ; git push --tags
#
#


set -e

cd $(dirname $0)/..

[ $(git status --short --untracked-files=no | wc -l) -gt 0 ] && {
	echo ""
	echo "WARN: the working directory has uncommited changes"
	echo ""
	echo "Press ENTER to continue..."
	echo ""
	read
}

echo python daedalus_version.py | grep -q 'dev' && {
	echo ""
	echo "ERROR: Version information does NOT contains 'dev'"
	echo ""
	exit 1
}

if [ -z "$DONTTEST" ] ; then

	echo ""
	echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
	echo " Running tests (set DONTTEST to skip this)"
	echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
	echo ""

	./dev-scripts/test.sh

fi


#
#
# Set version
#
#


echo ""
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo " Removing -dev from daedalus_version.py"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo ""

python daedalus_version.py remove_dev

export VER="$(python daedalus_version.py)"

echo "Version: $VER"

echo $VER | grep -q 'dev' && {
	echo "ERROR: Version information contains 'dev'"
	exit 1
}

# Once we're sure daedalus_version.py hasn't '-dev', we set client's version
python daedalus_version.py set_version_of_client


#
#
#  By now, "daedalus_version.py" and "src-client/setup.py" have the
#    SAME version and WITHOUT '-dev'
#
#


# Now run 'setup.py sdist' to update MANIFEST
python setup.py sdist
( cd src-client/ ; python setup.py sdist )

# Add to git the files that we've changed, commit and tag the stable version
git add MANIFEST            src-client/MANIFEST
git add daedalus_version.py src-client/setup.py
git commit -m "Updated version to $VER"
git tag -a -m "Version $VER" "v$VER"
git tag -f stable


#
#
# Upload to PYPI
#
#


echo ""
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo " Uploading to PYPI"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo ""

python setup.py sdist upload
( cd src-client/ ; python setup.py sdist upload )


#
#
# Set version
#
#


echo ""
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo " Incrementing version"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo ""

python daedalus_version.py incr_patch_version
python daedalus_version.py add_dev

NEWVER="$(python daedalus_version.py)"

if [ "$VER" = "$NEWVER" ] ; then
	echo "ERROR: version on daedalus_version.py haven't changed"
	echo "Press ENTER to exit"
	exit 1
else
	git commit daedalus_version.py -m "Updated version to $NEWVER"
fi


#
#
# Push to GitHub
#
#


echo ""
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo " Press ENTER to push to GitHub"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo ""
read

git push
git push --tags

