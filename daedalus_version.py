MAJOR_VERSION = 0
MINOR_VERSION = 0
PATCH_VERSION = 7
EXTRA = ''

def get_daedalus_version():
    return "{0}.{1}.{2}{3}".format(MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION, EXTRA)

if __name__ == '__main__':
    print get_daedalus_version()
