#!/usr/bin/env python
import sys


def make_template(**kwargs):
    template = \
"""
[Unit]
Description=Editors' Notes renderer node server for {SITE_NAME}

[Service]
ExecStart={PROJECT_PATH}/lib/iojs-current/bin/iojs {PROJECT_PATH}/renderer/releases/current/src/server
Restart=always

StandardOutput=syslog
StandardError=syslog
SyslogIdentifier={SITE_NAME}.renderer

Environment="EDITORSNOTES_API_URL=http://{HOST}" "EDITORSNOTES_CLIENT_PORT={RENDERER_PORT}"



[Install]
WantedBy=multi-user.target
"""
    return template.format(kwargs)

if __name__ == '__main__':
    kwargs = {
        'SITE_NAME': sys.argv[1],
        'PROJECT_PATH': sys.argv[2],
        'HOST': sys.argv[3],
        'RENDERER_PORT': sys.argv[4],
    }
    print(make_template(**kwargs))
/
