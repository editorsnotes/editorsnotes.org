"""
Deployment environments
"""

from fabric.api import env, task

def make_basic_conf(hostname):
    "Add the basic env values for our server"
    env.hosts = [hostname]

    env.project_path = '/usr/local/projects/{}'.format(hostname)
    env.python = '/usr/bin/python2.7'

    env.uwsgi_conf_file = '/etc/uwsgi/sites/{}.ini'.format(hostname)
    env.uwsgi_uid = 'ryanshaw'
    env.uwsgi_gid = 'ryanshaw'
    env.uwsgi_service_uid = 'ryanshaw'
    env.uwsgi_service_gid = 'ryanshaw'
    env.uwsgi_socket_location = '/run/uwsgi/{}.sock'.format(hostname)
    env.uwsgi_socket_uid = 'www-data'
    env.uwsgi_socket_gid = 'www-data'
    env.uwsgi_socket_chmod = 644

    env.nginx_conf_file = '/etc/nginx/conf.d/{}.conf'.format(hostname)

@task
def working_notes_test():
    "Use the main Working Notes host."
    hostname = 'test.workingnotes.org'
    make_basic_conf(hostname)
    env.renderer_port = 15023

@task
def working_notes():
    "Use the testing Working Notes host."
    hostname = 'workingnotes.org'
    make_basic_conf(hostname)
    env.renderer_port = 15024

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
ENVS = [
    beta,
    pro,
    working_notes,
    working_notes_test,
    'Custom host defined in fabfile_local.py'
]
