#!/usr/bin/env python

import sys

template = """[Unit]
Description=Editors' Notes markup renderer node server for {HOST}

[Service]
ExecStart={NODE_BIN}\
 {PROJECT_PATH}/markup_renderer/node_modules/.bin/editorsnotes_renderer\
 --port={MARKUP_RENDERER_PORT}

Restart=always

StandardOutput=syslog
StandardError=syslog
SyslogIdentifier={HOST}.markup-renderer

BindsTo={HOST}.target

[Install]
WantedBy=multi-user.target
"""

if __name__ == '__main__':
    print template.format(**{
        'HOST': sys.argv[1],
        'NODE_BIN': sys.argv[2],
        'PROJECT_PATH': sys.argv[3],
        'MARKUP_RENDERER_PORT': sys.argv[4],
    })
