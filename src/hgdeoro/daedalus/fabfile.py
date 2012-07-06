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
from fabric.utils import abort, warn
from fabric.tasks import execute

#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Cassandra installer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# The path to the Cassandra installer in TGZ format could be overriden using
#   the environment variable CASSANDRA_TGZ_INSTALLER (in this case, you should
#   set CASSANDRA_INSTALL_DIR too).
#
# By default, this script looks for the file 'apache-cassandra-1.1.2-bin.tar.gz'
#   in the 'root' of the project. You can make it with
# $ cd /path/to/daedalus
# $ ln -s /path/to/apache-cassandra-1.1.2-bin.tar.gz  .
#
# If you create this link (or copy the real file), you won't have
# to specify CASSANDRA_TGZ_INSTALLER nor CASSANDRA_INSTALL_DIR.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# JDK installer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# The path to the JDK installer could be overwriden using
#   the environment variable JDK_BIN_INSTALLER (in this case, you
#   should set JDK_INSTALL_DIR too).
#
# By default, this script looks for the file 'jdk-6u32-linux-x64.bin'
#   in the 'root' of the project. You can make it with
# $ cd /path/to/daedalus
# $ ln -s /path/to/jdk-6u32-linux-x64.bin  .
#
# If you create this link (or copy the real file), you won't have
# to specify JDK_BIN_INSTALLER nor JDK_INSTALL_DIR.


#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EXAMPLE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# 1) Download 'jdk-6u32-linux-x64.bin' and 'apache-cassandra-1.1.2-bin.tar.gz'
#   and put them on the 'root' of the project (in the same level of 'src', 'web', etc)
#
# 2) Run:
#   $ ./virtualenv/bin/fab -f src/hgdeoro/daedalus/fabric/fabfile.py -H root@192.168.122.77 install_all
#
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EXAMPLE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# To install JDK, Cassandra, and Daedalus on host 192.168.122.77, run:
#
# $ export CASSANDRA_TGZ_INSTALLER=/path/to/apache-cassandra-1.1.2-bin.tar.gz
# $ export CASSANDRA_INSTALL_DIR=apache-cassandra-1.1.2
# $ export JDK_BIN_INSTALLER=/path/to/jdk-6u21-linux-x64.bin
# $ export JDK_INSTALL_DIR=jdk1.6.0_21
# $ ./virtualenv/bin/fab -f src/hgdeoro/daedalus/fabric/fabfile.py -H root@192.168.122.77 install_all
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
def install_centos_packages():
    """
    Installs required packages on CentOS.
    """
    run("yum install --assumeyes "
        "gcc.x86_64 memcached python-devel.x86_64 zlib-devel.x86_64 "
        "memcached memcached-devel libmemcached-devel nginx")


@ task
def install_ubuntu_packages():
    """
    Installs required packages on Ubuntu.
    """
    run("aptitude install -y "
        "gcc memcached python-dev nginx"
        " libmemcached-dev zlib1g-dev")


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


#@task
#def install_cassandra_init_scripts():
#    pass


@ task
def launch_cassandra():
    """
    Launch Cassandra on VM.
    """
    if not exists("/opt/daedalus.jdk"):
        abort("/opt/daedalus.jdk doesn't exists on server. Install the JDK and retry.")
    if not exists("/opt/daedalus.cassandra"):
        abort("/opt/daedalus.cassandra doesn't exists on server. Install Cassandra and retry.")
    run("nohup su -c 'env JAVA_HOME=$(cat /opt/daedalus.jdk) "
        "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/root/bin "
        "$(cat /opt/daedalus.cassandra)/bin/cassandra "
        "-f -p {0} &' > /tmp/1 2> /tmp/2 < /dev/null".format(CASSANDRA_PID))


@ task
def shutdown_cassandra():
    """
    Shutdown Cassandra
    """
    if exists(CASSANDRA_PID):
        run("kill $(cat {0}) || true".format(CASSANDRA_PID))
        run("test -e {0} && rm {0}".format(CASSANDRA_PID))
    else:
        warn("Can't stop Cassandra: pid file not found")


@ task
def tail_cassandra():
    """
    Run 'tail -f' on Cassandra logs
    """
    run("tail -f /var/log/cassandra/*.log")


@ task
def install_all():
    execute(install_jdk)
    execute(install_cassandra)
    execute(launch_cassandra) # Launch Cassandra as soon as possible
    execute(install_daedalus)
    execute(syncdb_cassandra)


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


#@task
#def install_daedalus_init_scripts():
#    pass


@ task
def setup_virtualenv():
    """
    Installs virtualenv and pip requirements.
    """
    if not exists("~/.pip/pip.conf"):
        run("mkdir ~/.pip")
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


#@task
#def install_gunicorn_init_scripts():
#    pass

#@task
#def nginx_init_scripts():
#    pass

#@task
#def install_nginx_init_scripts():
#    pass


@task
def syncdb_cassandra():
    """
    Runs syncdb and syncdb_cassandra.
    """
    run("/opt/daedalus-dev/dev-scripts/manage.sh syncdb --noinput")
    run("/opt/daedalus-dev/dev-scripts/manage.sh syncdb_cassandra")