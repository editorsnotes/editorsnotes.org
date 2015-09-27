#!/usr/bin/env python

import sys

template = """[Unit]
Description=Editors' Notes uWSGI server for {HOST}
BindsTo={HOST}.target

[Service]
ExecStart={UWSGI_BIN}\
 --uid {UWSGI_SERVICE_USER} --gid {UWSGI_SERVICE_GROUP}\
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
        'UWSGI_BIN': sys.argv[2],
        'UWSGI_SERVICE_GROUP': sys.argv[3],
        'UWSGI_SERVICE_USER': sys.argv[4],
        'UWSGI_CONF_FILE': sys.argv[5],
    })
