MAJOR_VERSION=0
MINOR_VERSION=0
PATCH_VERSION=9
EXTRA='-dev'

def get_daedalus_version():
    return "{0}.{1}.{2}{3}".format(MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION, EXTRA)

if __name__ == '__main__':
    import sys
    import os
    import subprocess
    if len(sys.argv) == 1:
        print get_daedalus_version()
    elif "add_dev" in sys.argv:
        filename = os.path.abspath(__file__)
        print "Adding '-dev' to EXTRA"
        print subprocess.check_output(["sed", "-i", "-e", "s/^EXTRA=''/EXTRA='-dev'/", filename, ])
    elif "remove_dev" in sys.argv:
        filename = os.path.abspath(__file__)
        print "Removing '-dev' from EXTRA"
        print subprocess.check_output(["sed", "-i", "-e", "s/^EXTRA='-dev'/EXTRA=''/", filename, ])
    elif "incr_patch_version" in sys.argv:
        filename = os.path.abspath(__file__)
        new_patch_version = PATCH_VERSION + 1
        print "Incrementing PATCH_VERSION from {0} to {1}".format(PATCH_VERSION, new_patch_version)
        print subprocess.check_output(["sed", "-i", "-e",
            "s/^PATCH_VERSION={0}/PATCH_VERSION={1}/".format(PATCH_VERSION, new_patch_version), filename, ])
    elif "set_version_of_client" in sys.argv:
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src-client', 'setup.py')
        filename = os.path.abspath(filename)
        assert os.path.exists(filename)
        version = get_daedalus_version()
        print "Seting VERSION to {0}".format(version)
        print subprocess.check_output(["sed", "-i", "-e",
            "s/^VERSION = '.*'/VERSION = '{0}'/".format(version), filename, ])
    else:
        raise(Exception("Action not valid: " + sys.argv))
