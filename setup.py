import os

from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES
from setuptools import find_packages

#----------------------------------------------------------------------
# Release instructions
#----------------------------------------------------------------------
#
#  + remove '-dev' from version of setup.py
#  + git commit setup.py -m "Updated setup: version=v$(./virtualenv/bin/python setup.py --version)"
#  + git tag -a -m "Version $(./virtualenv/bin/python setup.py --version)" "v$(./virtualenv/bin/python setup.py --version)"
#  + increment version number and add '-dev' on version of setup.py
#  + git commit setup.py -m "Updated setup: version=v$(./virtualenv/bin/python setup.py --version)"
#  + git push --tags
#

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

    walk_directory = os.path.join(base_directory, 'web')
    for dirpath, dirnames, filenames in os.walk(walk_directory):
        # dirpath -> absolute path
        # relative_dirpath -> relative to 'base_directory'
        relative_dirpath = dirpath[(len(base_directory)+1):]
        data_files.append([
            relative_dirpath,
            [os.path.join(relative_dirpath, f) for f in filenames]
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
    name="Daedalus",
    version="0.0.2-dev",
    description='Django application to store log messages on Cassandra',
    author="Horacio G. de Oro",
    author_email="hgdeoror@gmail.com",
    url="https://github.com/hgdeoro/daedalus",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'pycassa', #'pycassa==1.6.0',
        'django', #'Django==1.4',
        'pylibmc', #'pylibmc==1.2.3',
    ],
    classifiers=classifiers, 
    data_files=gen_data_files(), 
)
