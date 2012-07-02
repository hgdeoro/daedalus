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


@task
def reset_test_vm():
    """
    Runs the `reset-kvm-test-vm.sh` script.
    This scripts DESTROYS the test VM and disk images and re-creates it.
    """
    shell_script = os.path.join(BASE_DIRECTORY, "dev-scripts", "reset-kvm-test-vm.sh")
    local("sudo -E {0}".format(shell_script))


@task
def start_test_vm():
    """
    Runs the `start-kvm-test-vm.sh` script: starts the VM and waits until it responds to pings.
    """
    shell_script = os.path.join(BASE_DIRECTORY, "dev-scripts", "start-kvm-test-vm.sh")
    local("sudo -E {0}".format(shell_script))


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
        "/var/lib/cassandra")
