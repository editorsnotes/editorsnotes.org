#!/usr/bin/env python
import sys


def make_template(**kwargs):
    template = \
"""
[Unit]
Description=Editors' Notes uWSGI server for {SITE_NAME}

[Service]
ExecStart=/usr/local/bin/uwsgi --uid {SOCKET_USER} --gid {SOCKET_GROUP} --ini {UWSGI_CONF_FILE}
Restart=always
Type=notify
NotifyAccess=all

[Install]
WantedBy=multi-user.target
"""
    return template.format(kwargs)

if __name__ == '__main__':
    kwargs = {
        'SITE_NAME': sys.argv[1],
        'SOCKET_GROUP': sys.argv[2],
        'SOCKET_USER': sys.argv[3],
        'UWSGI_CONF_FILE': sys.argv[4],
    }
    print(make_template(**kwargs))
