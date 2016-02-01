#!/usr/bin/env python

import sys

template = """[Unit]
Description=Editors' Notes renderer node server for {HOST}
BindsTo={HOST}.target

[Service]
ExecStart={NODE_BIN} {PROJECT_PATH}/renderer/releases/current/bin/serve.js
Restart=always

StandardOutput=syslog
StandardError=syslog
SyslogIdentifier={HOST}.renderer

Environment=\
 "EDITORSNOTES_API_URL=http://{HOST}"\
 "EDITORSNOTES_RENDERER_PORT={RENDERER_PORT}"\
 "NODE_ENV=production"

[Install]
WantedBy=multi-user.target
"""

if __name__ == '__main__':
    print template.format(**{
        'HOST': sys.argv[1],
        'NODE_BIN': sys.argv[2],
        'PROJECT_PATH': sys.argv[3],
        'RENDERER_PORT': sys.argv[4],
    })
