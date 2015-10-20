#!/usr/bin/env python

import sys

template_head = """# vim set filetype=conf

server {{
    listen 80;
    server_name {HOST};
"""

ssl_template_head = """
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl;
    server_name {HOST};

    include {SSL_CONF_FILE};

    if ($host != {HOST}) {
        return 444;
    }
"""

template = """
    #################
    # Configuration #
    #################

    set $project_dir {PROJECT_PATH};
    set $en_api_uwsgi unix:{UWSGI_SOCKET_LOCATION};
    set $en_renderer_http http://127.0.0.1:{RENDERER_PORT};


    ################
    #    Routes    #
    ################

    location / {{
        # Rewrite `Host` to this server name
        proxy_pass_request_headers on;
        proxy_set_header Host $http_host;

        # If accept HTML, proxy to editorsnotes-renderer
        if ($http_accept ~* "html") {{
            proxy_pass $en_renderer_http;
            break;
        }}

        # Else, pass to editorsnotes-api
        include uwsgi_params;
        uwsgi_pass $en_api_uwsgi;
    }}

    # Proxy to Django for authentication, regardless of media type
    location /auth/ {{
        proxy_pass_request_headers on;
        proxy_set_header Host $http_host;
        include uwsgi_params;
        uwsgi_pass $en_api_uwsgi;
    }}

    # Static files
    location /static/ {{
        root $project_dir/renderer/releases/current/;
    }}

    # Static file for authentication page
    location /static/admin_compiled.css {{
        root $project_dir;
    }}

    # Image uploads
    location /media/ {{
        alias $project_dir/uploads/;
    }}
}}
"""

if __name__ == '__main__':
    template_dict = {
        'HOST': sys.argv[1],
        'PROJECT_PATH': sys.argv[2],
        'UWSGI_SOCKET_LOCATION': sys.argv[3],
        'RENDERER_PORT': sys.argv[4],
    }
    template_start = template_head.format(**template_dict)

    try:
        template_dict['SSL_CONF_FILE'] = sys.argv[5]
        template_start += ssl_template_head.format(**template_dict)
    except IndexError:
        pass

    print template_start + template.format(**template_dict)
