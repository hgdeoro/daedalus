# -*- coding: utf-8 -*-

##-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
##    daedalus - Centralized log server
##    Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
##
##    This file is part of daedalus.
##
##    daedalus is free software; you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation version 2.
##
##    daedalus is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License version 2 for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with daedalus; see the file LICENSE.txt.
##-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

import os

from fabric.decorators import task
from fabric.operations import local, put, run
from fabric.context_managers import cd
from fabric.contrib.files import exists
from fabric.utils import abort
from fabric.tasks import execute

#
# This fabric script is used to test Daedalus on a VM.
# This must be run with something like:
#
# $ ./virtualenv/bin/fab -f src/hgdeoro/daedalus/fabfile.py -H root@vm install_all
#
# PLEASE, DO NOT use this script to install Daedalus / Cassandra in production systems!
#

#
# The path to the Cassandra installer in TGZ format could be overriden using
#   the environment variable JDK_INSTALL_DIR (in this case, you should
#   set CASSANDRA_INSTALL_DIR too).
#
# The path to the JDK installer could be overwriden using
#   the environment variable JDK_BIN_INSTALLER (in this case, you
#   should set JDK_INSTALL_DIR too).
#

# Base directory of Daedalus
BASE_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# TGZ file of Cassandra
CASSANDRA_TGZ_INSTALLER = os.path.join(BASE_DIRECTORY, "apache-cassandra-1.1.2-bin.tar.gz")

# Name of the directory created upon decompression of the TGZ
CASSANDRA_INSTALL_DIR = "apache-cassandra-1.1.2"

# JDK installer (.bin)
JDK_BIN_INSTALLER = os.environ.get('JDK_BIN_INSTALLER',
    os.path.join(BASE_DIRECTORY, "jdk-6u32-linux-x64.bin"))

# Name of the directory that the JDK installer creates
JDK_INSTALL_DIR = os.environ.get('JDK_INSTALL_DIR', "jdk1.6.0_32")

CASSANDRA_PID = "/var/log/cassandra/cassandra.pid"

EPEL_RPM = "http://dl.fedoraproject.org/pub/epel/6/i386/epel-release-6-7.noarch.rpm"

#@task
#def reset_test_vm():
#    """
#    Runs the `reset-kvm-test-vm.sh` script.
#    This scripts DESTROYS the test VM and disk images and re-creates it.
#    """
#    shell_script = os.path.join(BASE_DIRECTORY, "dev-scripts", "reset-kvm-test-vm.sh")
#    local("sudo -E {0}".format(shell_script))


@task
def start_test_vm():
    """
    Runs the `start-kvm-test-vm.sh` script: starts the VM and waits until it responds to pings.
    """
    shell_script = os.path.join(BASE_DIRECTORY, "dev-scripts", "start-kvm-test-vm.sh")
    local("sudo -E {0}".format(shell_script))


@ task
def install_epel():
    """
    Register EPEL repository.
    """
    run("curl -o /tmp/epel.rpm {0}".format(EPEL_RPM))
    run("rpm -i /tmp/epel.rpm")


@ task
def install_packages():
    """
    Installs requeriments on CentOS.
    """
    run("yum install --assumeyes "
        "gcc.x86_64 memcached python-devel.x86_64 zlib-devel.x86_64 "
        "memcached memcached-devel libmemcached-devel nginx")


@ task
def install_jdk():
    """
    Installs JDK
    """
    if not exists("/opt/{0}".format(JDK_INSTALL_DIR)):
        installer_name = os.path.basename(JDK_BIN_INSTALLER)
        dest_file = "/tmp/{0}".format(installer_name)
        if not exists(dest_file):
            put(JDK_BIN_INSTALLER, dest_file)
        run("chmod +x /tmp/{0}".format(installer_name))
        with cd("/opt"):
            run("/tmp/{0} < /dev/null".format(installer_name))
        run("echo /opt/{0} > /opt/daedalus.jdk".format(
            JDK_INSTALL_DIR))


@ task
def install_cassandra():
    """
    Installs Cassandra
    """
    # TODO: if `CASSANDRA_TGZ` doesn't exists, exit with error and instructions
    if not exists("/opt/{0}".format(CASSANDRA_INSTALL_DIR)):
        installer_name = os.path.basename(CASSANDRA_TGZ_INSTALLER)
        dest_file = "/tmp/{0}".format(installer_name)
        if not exists(dest_file):
            put(CASSANDRA_TGZ_INSTALLER, dest_file)
        run("tar -C /opt -xzf {0}".format(dest_file))
        run("echo /opt/{0} > /opt/daedalus.cassandra".format(
            CASSANDRA_INSTALL_DIR))
    run("mkdir -p "
        "/var/log/cassandra "
        "/var/lib/cassandra/data "
        "/var/lib/cassandra/commitlog "
        "/var/lib/cassandra/saved_caches")


@ task
def launch_cassandra():
    """
    Launch Cassandra on VM
    """
    if not exists("/opt/daedalus.jdk"):
        abort("/opt/daedalus.jdk doesn't exists on server. Install the JDK and retry.")
    if not exists("/opt/daedalus.cassandra"):
        abort("/opt/daedalus.cassandra doesn't exists on server. Install Cassandra and retry.")
    run("env JAVA_HOME=$(cat /opt/daedalus.jdk) "
        "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/root/bin "
        "$(cat /opt/daedalus.cassandra)/bin/cassandra "
        "-f -p {0}".format(CASSANDRA_PID))


@ task
def shutdown_cassandra():
    """
    Shutdown Cassandra
    """
    if exists(CASSANDRA_PID):
        run("kill $(cat {0}) || true".format(CASSANDRA_PID))
        run("test -e {0} && rm {0}".format(CASSANDRA_PID))


@ task
def install_all():
    execute(install_jdk)
    execute(install_cassandra)
    execute(install_daedalus)


@ task
def uninstall_all():
    execute(shutdown_cassandra)
    if exists("/opt/daedalus.jdk"):
        run("test -e /opt/daedalus.jdk && "
            "{ rm -rf $(cat /opt/daedalus.jdk) ; rm /opt/daedalus.jdk ; }")
    if exists("/opt/daedalus.cassandra"):
        run("test -e /opt/daedalus.cassandra && "
            "{ rm -rf $(cat /opt/daedalus.cassandra) ; rm /opt/daedalus.cassandra ; }")
    run("rm -rf "
        "/var/log/cassandra "
        "/var/lib/cassandra "
        "/opt/daedalus-dev "
        "/opt/virtualenv")


@ task
def install_daedalus():
    """
    Installs daedalus in the testing VM.
    """
    local("git archive --format=tar --prefix=daedalus-dev/ HEAD | gzip "
        "> /tmp/daedalus-dev.tgz")
    put("/tmp/daedalus-dev.tgz", "/tmp/daedalus-dev.tgz")
    if exists("/opt/daedalus-dev"):
        run("rm -rf /opt/daedalus-dev")
    run("tar -C /opt -xzf /tmp/daedalus-dev.tgz")
    run("echo 'CACHES = {}' > /opt/daedalus-dev/src/daedalus_local_settings.py")
    run("echo 'DAEDALUS_FORCE_SERVING_STATIC_FILES = True' >> "
        "/opt/daedalus-dev/src/daedalus_local_settings.py")
    execute(setup_virtualenv)
    execute(syncdb_cassandra)


@ task
def setup_virtualenv():
    """
    Installs virtualenv and pip requirements.
    """
    if not exists("~/.pip/pip.conf"):
        run("echo '[install]' > ~/.pip/pip.conf")
        run("echo 'download-cache = ~/pip-cache' >> ~/.pip/pip.conf")
        run("mkdir ~/pip-cache")

    if not exists("/opt/virtualenv"):
        if not exists("/tmp/virtualenv.py"):
            run("curl -o /tmp/virtualenv.py https://raw.github.com/pypa/virtualenv/master/virtualenv.py")
    
        run("python /tmp/virtualenv.py /opt/virtualenv")
        
    if not exists("/opt/daedalus-dev/virtualenv"):
        run("ln -s /opt/virtualenv /opt/daedalus-dev/virtualenv")

    run("/opt/virtualenv/bin/pip install -r /opt/daedalus-dev/requirements.txt")
    run("/opt/virtualenv/bin/pip install gunicorn")


@ task
def daedalus_test():
    """
    Runs the tests in the testing vm..
    """
    run("/opt/daedalus-dev/dev-scripts/test.sh")


@task
def run_gunicorn():
    """
    Launches gunicorn
    """
    run("/opt/daedalus-dev/dev-scripts/gunicorn.sh")


@task
def syncdb_cassandra():
    """
    Runs syncdb and syncdb_cassandra.
    """
    run("/opt/daedalus-dev/dev-scripts/manage.sh syncdb --noinput")
    run("/opt/daedalus-dev/dev-scripts/manage.sh syncdb_cassandra")
