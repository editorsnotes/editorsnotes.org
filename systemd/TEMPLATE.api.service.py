#!/usr/bin/env python

import sys

template = """[Unit]
Description=Editors' Notes uWSGI server for {HOST}

[Service]
ExecStart=/usr/local/bin/uwsgi\
 --uid {SOCKET_USER} --gid {SOCKET_GROUP}\
 --ini {UWSGI_CONF_FILE}

Restart=always
Type=notify
NotifyAccess=all

[Install]
WantedBy=multi-user.target
"""

if __name__ == '__main__':
    print template.format(**{
        'HOST': sys.argv[1],
        'SOCKET_GROUP': sys.argv[2],
        'SOCKET_USER': sys.argv[3],
        'UWSGI_CONF_FILE': sys.argv[4],
    })
