"""
Deployment environments
"""

from fabric.api import env, task

@task
def working_notes_test():
    "Use the beta-testing webserver."
    env.project_name = 'workingnotes-test'
    env.hosts = ['test.workingnotes.org']

    env.project_path = '/db/projects/{project_name}'.format(**env)
    env.python = '/usr/bin/python2.7'

    env.uwsgi_uid = 'patrick'
    env.uwsgi_gid = 'patrick'
    env.uwsgi_socket_location = '/run/uwsgi/{project_name}'.format(**env)
    env.uwsgi_socket_uid = 'www-data'
    env.uwsgi_socket_gid = 'www-data'
    env.uwsgi_socket_chmod = 644

@task
def beta():
    "Use the beta-testing webserver."
    env.name = 'beta.editorsnotes.org'
    env.hosts = ['beta.editorsnotes.org']

    env.project_path = '/db/projects/{project_name}-beta'.format(**env)
    env.vhosts_path = '/etc/httpd/sites.d'
    env.python = '/usr/bin/python2.7'


@task
def pro():
    "Use the production webserver."
    env.hosts = ['editorsnotes.org']
    env.project_path = '/db/projects/{project_name}'.format(**env)
    env.vhosts_path = '/etc/httpd/sites.d'
    env.python = '/usr/bin/python2.7'

try:
    from fabfile_local import *
except ImportError:
    pass

# Create custom environments in fabfile_local.py, in the same style as above
ENVS = [beta, pro, 'Custom host defined in fabfile_local.py']
