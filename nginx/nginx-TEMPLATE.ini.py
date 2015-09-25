#!/usr/bin/env python
import sys


def make_template(**kwargs):
    template = \
"""
# vim set filetype=conf

server {
        #################
        # Configuration #
        #################

        listen 80;
        server_name {HOST};

        set $project_dir {PROJECT_PATH}/renderer/releases/current;
        set $en_api_uwsgi unix:{UWSGI_SOCKET_LOCATION};
        set $en_renderer_http http://{HOST}:{RENDERER_PORT};


        ################
        #    Routes    #
        ################

        location / {
                # Rewrite `Host` to this server name
                proxy_pass_request_headers on;
                proxy_set_header Host $http_host;

                # If accept HTML, proxy to editorsnotes-renderer
                if ($http_accept ~* "html") {
                        proxy_pass $en_renderer_http;
                        break;
                }

                # Else, pass to editorsnotes-api
                include uwsgi_params;
                uwsgi_pass $en_api_uwsgi;
        }

        # Proxy to Django for authentication, regardless of media type
        location /auth/ {
                proxy_pass_request_headers on;
                proxy_set_header Host $http_host;
                include uwsgi_params;
                uwsgi_pass $en_api_uwsgi;
        }

        # Static files
        location /static/ {
                root $project_dir/;
        }

        # Image uploads
        location /media/ {
                alias $project_dir/uploads/;
        }
}
"""
    return template.format(kwargs)

if __name__ == '__main__':
    kwargs = {
        'HOST': sys.argv[1],
        'PROJECT_PATH': sys.argv[2],
        'UWSGI_SOCKET_LOCATION': sys.argv[3],
        'RENDERER_PORT': sys.argv[4],
    }
    print(make_template(**kwargs))
