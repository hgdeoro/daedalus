import os

from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES
from distutils.util import convert_path

"""
This is the setup file for the Daedalus server, which includes:
- Backend: what receives the messages
- Frontend: webapp to see the messages
- Python client: library to send messages messages to Daedalus from Python
- Loggin handler: to attach to Python's logging framework and send log messages to Daedalus

The `setup.py` file is fot the entire project.
The `setup_client.py` is for the Python client and logging handler: this exists
to avoid installing the whole projet in the cases where only the client is needed.
"""

#----------------------------------------------------------------------
# Release instructions --> USE `do-release.sh`
#----------------------------------------------------------------------

VERSION = __import__('daedalus_version').get_daedalus_version()

def gen_data_files():
    """
    Generates a list of items suitables to be used as 'data_files' parameter of setup().
    Something like:
        ('web/frontend/static/bootstrap-2.0.4/css', [
            'web/frontend/static/bootstrap-2.0.4/css/bootstrap-responsive.css', 
            'web/frontend/static/bootstrap-2.0.4/css/bootstrap.css', 
            ]),
    """
    base_directory = os.path.split(__file__)[0]
    base_directory = os.path.abspath(base_directory)
    base_directory = os.path.normpath(base_directory)

    data_files = []

    walk_directory = os.path.join(base_directory, 'src')
    for dirpath, dirnames, filenames in os.walk(walk_directory):
        # dirpath -> absolute path
        # relative_dirpath -> relative to 'base_directory'
        relative_dirpath = dirpath[(len(base_directory)+1):]
        dest_path = dirpath[(len(walk_directory)+1):]
        data_files.append([
            dest_path,
            [os.path.join(relative_dirpath, f) for f in filenames if not f.endswith('.pyc') and not f.endswith('.py')]
        ])

    return data_files

# http://pypi.python.org/pypi?%3Aaction=list_classifiers
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Web Environment",
    "Framework :: Django",
    "Intended Audience :: Information Technology",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    "Operating System :: Unix",
    "Programming Language :: Python",
    "Topic :: Internet :: Log Analysis",
    "Topic :: System :: Logging",
    "Topic :: System :: Systems Administration",
]

for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']

setup(
    name="daedalus",
    version=VERSION,
    description='Django application to store log messages on Cassandra',
    author="Horacio G. de Oro",
    author_email="hgdeoror@gmail.com",
    url="https://github.com/hgdeoro/daedalus",
    packages=[
        'daedalus',
        'daedalus.frontend',
        'daedalus.frontend.templatetags',
        'daedalus.backend',
        'daedalus.backend.management',
        'daedalus.backend.management.commands',
    ],
    package_dir={'': 'src'},
    install_requires=[
        'pycassa==1.6.0',
        'django==1.11.29',
        'python-memcached',
        'pytz',
        'daedalus-python-client',
    ],
    classifiers=classifiers, 
    data_files=[('', ['daedalus_version.py'])] + gen_data_files(),
)
