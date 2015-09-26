Deployment settings for editorsnotes.org.


# Prerequisites and setup

In additions to the requirements for [the `editorsnotes` API], the following
packages are required:

  1. nginx
  2. uwsgi

Before running any commands, you must define two environment variables:

  1. `EDITORSNOTES\_GIT`

     The directory where you keep an `editorsnotes` API git repository
     (i.e. `/Library/patrick/projects/editorsnotes`).

  2. `EDITORSNOTES\_RENDERER\_GIT`

     The directory where you keep an `editorsnotes-renderer` git repository
     (i.e. `/Library/patrick/projects/editorsnotes-renderer`).


# Defining an environment

After installing all requirements, create a new [fabric task] in a file called
`fabfile_local.py` that will define a [fabric environment] for your server.
This environment will provide configuration for the remote tasks you will
perform while deploying Editors' Notes.

All environments defined in `fabfile_local.py` will be imported into `envs.py`.

Example environments can be found in `envs.py`. Here is how an environment
might look for a deployment at `editorsnotes.local`:

```python
# file: fabfile_local.py

from fabric.api import env, task

@task
def editorsnotes_local_environment():
    "Use editorsnotes.local host"
    env.hosts = ['editorsnotes.local']

    env.project_path = '/projects/editorsnotes-local'
    env.python = '/usr/bin/python2.7'

    env.uwsgi_conf_file = '/etc/uwsgi/sites/editorsnotes.local.ini'
    env.uwsgi_uid = 'patrick'
    env.uwsgi_gid = 'patrick'
    env.uwsgi_service_uid = 'patrick'
    env.uwsgi_service_gid = 'patrick'
    env.uwsgi_socket_location = '/run/uwsgi/editorsnotes.local.sock'
    env.uwsgi_socket_uid = 'www-data'
    env.uwsgi_socket_gid = 'www-data'
    env.uwsgi_socket_chmod = 644

    env.nginx_conf_file = '/etc/nginx/conf.d/editorsnotes.local.conf'
    env.renderer_port = 15023
```

# Service configuration files

Once you have defined an environment, you must create configuration files for
the uWSGI, NGINX, and Systemd services that run Editors' Notes. This can be
done by running the `create_confs` task. For example, to create configuration
files for the environment we defined above, run:

  `fab envs.editorsnotes_local_environment create_confs`


# Deployment

Deployment is done with the `full_deploy` task:

  `fab envs.editorsnotes_local_environment full_deploy`

This will deploy `HEAD` from both the API and Renderer repositories. To define
specific versions to deploy, add arguments for API and Renderer git tags:

  `fab envs.editorsnotes_local_environment full_deploy:api_version=2.3.0,renderer_version=3.4.1`


[The `editorsnotes` API]: https://github.com/editorsnotes/editorsnotes#installation
[fabric task]: http://docs.fabfile.org/en/1.10/api/core/tasks.html
[fabric environment]: http://docs.fabfile.org/en/1.10/usage/env.html
