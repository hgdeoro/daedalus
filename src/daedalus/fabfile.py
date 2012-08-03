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
from fabric.context_managers import hide
from fabric.contrib.files import exists
from fabric.utils import abort, warn
from fabric.tasks import execute

"""
This fabric script is intended to automate the testing of Daedalus in virtual machines
with different Linux distributions.

Java/JDK: to lower the complexity I have removed the installation of
the JDK since it's difficult to automate (now the distribution's JDK is used).

Cassandra: is installed from the official .deb package on Ubuntu, and from the
Riptano repository on CentOS.
 To install other version, see the fabric task: `custom_cassandra_install()`
"""

# Base directory of Daedalus
BASE_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# TGZ file of Cassandra
CASSANDRA_TGZ_INSTALLER = os.path.join(BASE_DIRECTORY, "apache-cassandra-1.1.2-bin.tar.gz")

# Name of the directory created upon decompression of the TGZ
# TODO: this could be automatized!
CASSANDRA_INSTALL_DIR = "apache-cassandra-1.1.2"

CASSANDRA_PID = "/var/log/cassandra/cassandra.pid"

EPEL_RPM = "http://dl.fedoraproject.org/pub/epel/6/i386/epel-release-6-7.noarch.rpm"

CASSANDRA_DEB_URL = "http://www.apache.org/dist/cassandra/debian/pool/main/c/cassandra/cassandra_1.1.2_all.deb"


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Utility methods
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def get_run_output(*args, **kwargs):
    """
    Ejecuta comando en OpenWrt y devuleve (ret.stdout, ret).

    Ejemplo:
        out, _ = get_run_output("ls -lh /")
    """
    with hide('stdout'):
        ret = run(*args, **kwargs)
    return ret.stdout, ret


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Task: VM management
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#@task
#def reset_test_vm():
#    """
#    Runs the `reset-kvm-test-vm.sh` script.
#    This scripts DESTROYS the test VM and disk images and re-creates it.
#    """
#    shell_script = os.path.join(BASE_DIRECTORY, "dev-scripts", "reset-kvm-test-vm.sh")
#    local("sudo -E {0}".format(shell_script))

#@task
#def start_test_vm(vm_name=None):
#    """
#    Runs the `start-kvm-test-vm.sh` script: starts the VM and waits until it responds to pings.
#
#    Parameters:
#    - vm_name: name of the VM managed using `libvirt`, and also the name of the host
#    (this name should respond to pings, so this scripts detect when the VM is up).
#    """
#    shell_script = os.path.join(BASE_DIRECTORY, "dev-scripts", "start-kvm-test-vm.sh")
#    if vm_name is not None:
#        local("sudo -E DAEDALUS_VM_NAME={1} {0}".format(shell_script, vm_name))
#    else:
#        local("sudo -E {0}".format(shell_script))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Task: CentOS
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@ task
def centos_install_epel():
    """
    Register EPEL repository.
    """
    if not exists("/etc/yum.repos.d/epel.repo"):
        run("curl -o /tmp/epel.rpm {0}".format(EPEL_RPM))
        run("rpm -i /tmp/epel.rpm")


@ task
def centos_install_packages():
    """
    Installs required packages on CentOS.
    """
    execute(centos_install_epel)
    run("yum install --assumeyes "
        "gcc.x86_64 memcached python-devel.x86_64 zlib-devel.x86_64 "
        "memcached memcached-devel libmemcached-devel nginx "
        "java-1.6.0-openjdk python-virtualenv")
    if not exists("/etc/yum.repos.d/riptano.repo"):
        put(os.path.join(BASE_DIRECTORY, "dev-scripts", "centos", "riptano.repo"),
            "/etc/yum.repos.d/riptano.repo")
    run("yum install --assumeyes apache-cassandra11")
    run("chkconfig --add cassandra")
    run("chkconfig cassandra on")
    run("service cassandra start")


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Task: Ubuntu
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@ task
def ubuntu_install_packages():
    """
    Installs required packages on Ubuntu.
    """
    run("aptitude install -y "
        "gcc memcached python-dev nginx "
        "libmemcached-dev zlib1g-dev openjdk-6-jdk "
        "python-virtualenv "
        "jsvc libcommons-daemon-java libjna-java "
        "python-support")
    cassandra_installed = get_run_output("dpkg --get-selections | cut -f 1 | egrep '^cassandra$' | wc -l")[0]
    if int(cassandra_installed) == 0:
        if not exists(CASSANDRA_DEB_URL.split("/")[-1]):
            run("wget {0}".format(CASSANDRA_DEB_URL))
        run("dpkg -i {0}".format(CASSANDRA_DEB_URL.split("/")[-1]))
    # TODO: Check available memory, and shoy BIG warning if < 1GiB


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Task: Custom Cassandra
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@ task
def custom_cassandra_install():
    """
    Installs Cassandra from a tarball

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Custom Cassandra installer
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    The path to the Cassandra installer in TGZ format could be overriden using
      the environment variable CASSANDRA_TGZ_INSTALLER (in this case, you should
      set CASSANDRA_INSTALL_DIR too).
    
    By default, this script looks for the file 'apache-cassandra-1.1.2-bin.tar.gz'
      in the 'root' of the project. You can make it with
    $ cd /path/to/daedalus
    $ ln -s /path/to/apache-cassandra-1.1.2-bin.tar.gz  .
    
    If you create this link (or copy the real file), you won't have
    to specify CASSANDRA_TGZ_INSTALLER nor CASSANDRA_INSTALL_DIR.

    Otherwise, set CASSANDRA_TGZ_INSTALLER and CASSANDRA_INSTALL_DIR.

    $ export CASSANDRA_TGZ_INSTALLER=/path/to/apache-cassandra-1.1.2-bin.tar.gz
    $ export CASSANDRA_INSTALL_DIR=apache-cassandra-1.1.2
    $ ./virtualenv/bin/fab -f src/daedalus/fabric/fabfile.py -H root@192.168.122.77 install_all
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
#def custom_cassandra_install_init_scripts():
#    pass


@ task
def custom_cassandra_launch():
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
def custom_cassandra_shutdown():
    """
    Shutdown Cassandra
    """
    if exists(CASSANDRA_PID):
        run("kill $(cat {0}) || true".format(CASSANDRA_PID))
        run("test -e {0} && rm {0}".format(CASSANDRA_PID))
    else:
        warn("Can't stop Cassandra: pid file not found")


@ task
def custom_cassandra_tail_logs():
    """
    Run 'tail -f' on Cassandra logs
    """
    run("tail -f /var/log/cassandra/*.log")


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Task: Daedalus
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@ task
def daedalus_uninstall():
    """
    Removes the installed version of Daedalus.
    """
    run("rm -rf "
        "/opt/daedalus-dev "
        "/opt/virtualenv")


@ task
def daedalus_reinstall():
    """
    (Re-)Installs daedalus in the testing VM.
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
    execute(daedalusl_virtualenv_setup)
    execute(daedalus_syncdb)


#@task
#def daedalus_install_init_scripts():
#    pass


@ task
def daedalusl_virtualenv_setup():
    """
    Installs virtualenv and pip requirements.
    """
    if not exists("~/.pip/pip.conf"):
        run("mkdir ~/.pip")
        run("echo '[install]' > ~/.pip/pip.conf")
        run("echo 'download-cache = ~/pip-cache' >> ~/.pip/pip.conf")
        run("mkdir ~/pip-cache")

    if not exists("/opt/virtualenv"):
        run("virtualenv --no-site-packages /opt/virtualenv")

    if not exists("/opt/daedalus-dev/virtualenv"):
        run("ln -s /opt/virtualenv /opt/daedalus-dev/virtualenv")

    run("/opt/virtualenv/bin/pip install -r /opt/daedalus-dev/requirements.txt")
    run("/opt/virtualenv/bin/pip install gunicorn")


@task
def daedalus_syncdb():
    """
    Runs syncdb and syncdb_cassandra.
    """
    run("/opt/daedalus-dev/dev-scripts/manage.sh syncdb --noinput")
    run("/opt/daedalus-dev/dev-scripts/manage.sh syncdb_cassandra")


@ task
def daedalus_test():
    """
    Runs the tests in the testing vm..
    """
    run("/opt/daedalus-dev/dev-scripts/test.sh")


@ task
def daedalus_insert_500_random():
    """
    Runs the tests in the testing vm..
    """
    run("env dont_drop_daedalus_tests=1 "
        "/opt/daedalus-dev/dev-scripts/test.sh backend.BulkSave.bulk_sparse_save_500")


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Task: Gunicorn
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@task
def gunicorn_launch():
    """
    Launches gunicorn
    """
    run("/opt/daedalus-dev/dev-scripts/gunicorn.sh")


#@task
#def gunicorn_install_init_scripts():
#    pass


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Task: Nginx
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#@task
#def nginx_install():
#    pass

#@task
#def nginx_install_init_scripts():
#    pass
