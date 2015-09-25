#!/usr/bin/env python
import sys

def make_template(**kwargs):
    template = \
"""
[uwsgi]
chdir = {root_dir}/api/releases/current
virtualenv = {root_dir}/api/venv
module = wsgi:application

master = true
processes = 1

uid = {uwsgi_uid}
gid = {uwsgi_gid}

socket = /run/uwsgi/{site_name}.sock
chown-socket = {socket_gid}:{socket_uid}
chmod-socket = {socket_chmod}

vacuum = true

die-on-term = true
"""
    return template.format(**kwargs)

if __name__ == '__main__':
    print make_template(**{
        'site_name': sys.argv[1],
        'root_dir': sys.argv[2],
        'uwsgi_gid': sys.argv[3],
        'uwsgi_uid': sys.argv[4],
        'socket_gid': sys.argv[5],
        'socket_uid': sys.argv[6],
        'socket_chmod': sys.argv[7]
    })
