#!/bin/bash

# Install required packages
aptitude install -y \
	gcc memcached python-dev nginx \
	libmemcached-dev zlib1g-dev openjdk-6-jre openjdk-6-jdk \
	gunicorn python-pylibmc python-virtualenv python-pip git \
	jsvc libcommons-daemon-java libjna-java

# Download and install Cassandra
wget http://www.apache.org/dist/cassandra/debian/pool/main/c/cassandra/cassandra_1.1.2_all.deb
dpkg -i cassandra_1.1.2_all.deb

# Clone (download) Daedalus
git clone https://github.com/hgdeoro/daedalus.git
cd daedalus

# Install required python libraries
pip install -r requirements.txt

# Optional: change to the 'stable' version
git checkout stable

# Setup Cassandra Keyspaces
./dev-scripts/manage.sh syncdb_cassandra

# Launch Daedalus, listening on all interfaces/IP on port 8080
./dev-scripts/manage.sh runserver 0.0.0.0:8080

