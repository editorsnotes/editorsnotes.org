#!/usr/bin/env python

import sys

template = """[uwsgi]
plugins = python

chdir = {ROOT_DIR}/api/releases/current
virtualenv = {ROOT_DIR}/api/venv
module = wsgi:application

master = true
processes = 1

# uid = {UWSGI_UID}
# gid = {UWSGI_GID}

socket = /run/uwsgi/{HOST}.sock
# chown-socket = {SOCKET_GID}:{SOCKET_UID}
chmod-socket = {SOCKET_CHMOD}

vacuum = true

die-on-term = true
"""

if __name__ == '__main__':
    print template.format(**{
        'HOST': sys.argv[1],
        'ROOT_DIR': sys.argv[2],
        'UWSGI_GID': sys.argv[3],
        'UWSGI_UID': sys.argv[4],
        'SOCKET_GID': sys.argv[5],
        'SOCKET_UID': sys.argv[6],
        'SOCKET_CHMOD': sys.argv[7]
    })
