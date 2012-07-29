from distutils.core import setup
#from distutils.command.install import INSTALL_SCHEMES

"""
This is the setup file for the Daedalus client, which includes:
- Python client: library to send messages messages to Daedalus from Python
- Loggin handler: to attach to Python's logging framework and send log messages to Daedalus

The `setup.py` file is fot the entire project.
The `setup_client.py` is for the Python client and logging handler: this exists
to avoid installing the whole projet in the cases where only the client is needed.
"""

# http://pypi.python.org/pypi?%3Aaction=list_classifiers
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Web Environment",
    "Intended Audience :: Information Technology",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    "Operating System :: Unix",
    "Programming Language :: Python",
    "Topic :: System :: Logging",
]

#for scheme in INSTALL_SCHEMES.values():
#    scheme['data'] = scheme['purelib']

# http://docs.python.org/distutils/extending.html
setup(
    name="daedalus-python-client",
    version="0.0.1",
    description='Python client to send messages to Daedalus.',
    author="Horacio G. de Oro",
    author_email="hgdeoror@gmail.com",
    url="https://github.com/hgdeoro/daedalus",
    packages=[''],
    py_modules=['daedalus_client', 'daedalus_logging_handler'],
    classifiers=classifiers,
)
