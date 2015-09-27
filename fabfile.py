# -*- coding: utf-8 -*-

from fabric.api import *
from fabric.colors import red
from fabric.contrib.console import confirm
from fabric.contrib.files import exists

import os
import sys
import time


# Namespaced fabric tasks
import envs
import api
import renderer
import markup_renderer


####################
# Global variables #
####################
env.project_name = 'editorsnotes'
env.release = time.strftime('%Y%m%d%H%M%S')
env.TMP_DIR = os.path.join(os.path.dirname(env.real_fabfile), 'tmp')

env.git = {}
env.git['api'] = os.getenv('EDITORSNOTES_API_GIT')
env.git['renderer'] = os.getenv('EDITORSNOTES_RENDERER_GIT')

if not env.git['api']:
    abort(red(
        'Set EDITORSNOTES_API_GIT environment variable with a path to an '
        'Editors\'s Notes API git repository.'
    ))

if not env.git['renderer']:
    abort(red(
        'Set EDITORSNOTES_API_RENDERER environment variable with a path to an '
        'Editors\'s Notes renderer git repository.'
    ))


#########
# Tasks #
#########

@task
def create_confs():
    create_uwsgi_conf()
    create_nginx_conf()
    create_api_service()
    create_renderer_service()
    create_markup_renderer_service()
    create_systemd_target()


def create_template(template_vars, template_script):
    require(*template_vars, provided_by=envs.ENVS)
    template_string = ' '.join(['{' + var + '}' for var in template_vars])

    template_command = (template_script + ' ' + template_string).format(**env)
    return local(template_command, capture=True)


def write_config(conf_type, filename, content):
    if os.path.exists(filename):
        msg = '{} configuration already exists at {}\nOverwrite?'.format(
            conf_type, filename)

        print ''

        if not confirm(msg):
            return

    with open(filename, 'w') as outfile:
        outfile.write(content)


@task
def create_uwsgi_conf():
    template_vars = [
        'host',
        'project_path',
        'uwsgi_gid',
        'uwsgi_uid',
        'uwsgi_socket_gid',
        'uwsgi_socket_uid',
        'uwsgi_socket_chmod'
    ]

    output_filename = 'uwsgi/uwsgi-{host}.ini'.format(**env)
    uwsgi_conf = create_template(
        template_vars, './uwsgi/uwsgi-TEMPLATE.ini.py')

    write_config('uWSGI', output_filename, uwsgi_conf)


@task
def create_nginx_conf():
    template_vars = [
        'host',
        'project_path',
        'uwsgi_socket_location',
        'renderer_port',
    ]

    output_filename = 'nginx/nginx-{host}.conf'.format(**env)
    nginx_conf = create_template(
        template_vars, './nginx/nginx-TEMPLATE.conf.py')

    write_config('Nginx', output_filename, nginx_conf)


@task
def create_systemd_target():
    template_vars = [
        'host'
    ]

    output_filename = 'systemd/{host}.target'.format(**env)
    systemd_target = create_template(
        template_vars, './systemd/TEMPLATE.target.py')

    write_config('Systemd target', output_filename, systemd_target)


@task
def create_api_service():
    template_vars = [
        'host',
        'uwsgi_bin',
        'uwsgi_service_gid',
        'uwsgi_service_uid',
        'uwsgi_conf_file',
    ]

    output_filename = 'systemd/{host}.api.service'.format(**env)
    api_service = create_template(
        template_vars, './systemd/TEMPLATE.api.service.py')

    write_config('API service', output_filename, api_service)


@task
def create_renderer_service():
    template_vars = [
        'host',
        'node_bin',
        'project_path',
        'renderer_port',
    ]

    output_filename = 'systemd/{host}.renderer.service'.format(**env)
    renderer_service = create_template(
        template_vars, './systemd/TEMPLATE.renderer.service.py')

    write_config('Renderer service', output_filename, renderer_service)


@task
def create_markup_renderer_service():
    template_vars = [
        'host',
        'node_bin',
        'project_path',
        'markup_renderer_port',
    ]

    output_filename = 'systemd/{host}.markup-renderer.service'.format(**env)
    renderer_service = create_template(
        template_vars, './systemd/TEMPLATE.markup-renderer.service.py')

    write_config('Markup renderer service', output_filename, renderer_service)


@task
def setup():
    """
    Setup all project directories.
    """
    require('hosts', 'project_path', provided_by=envs.ENVS)

    if not exists(env.project_path):
        abort(red('Project path ({project_path}) does not exist. '
                  'Create it on the server before continuing.'.format(**env)))

    with cd(env.project_path):
        run('mkdir -p api renderer lib conf markup_renderer')
        run('mkdir -p api/static api/uploads')

        make_release_folders('api')
        make_release_folders('renderer')


@task
def upload_uwsgi_conf():
    require('uwsgi_conf_file', 'host', provided_by=envs.ENVS)
    uwsgi_file = 'uwsgi/uwsgi-{host}.ini'.format(**env)

    check_file(uwsgi_file)

    put(uwsgi_file, '{project_path}/conf/uwsgi.ini.tmp'.format(**env))
    with cd(env.project_path):
        sudo('chmod 644 conf/uwsgi.ini.tmp')
        sudo('chown root:root conf/uwsgi.ini.tmp')
        sudo('mv -f conf/uwsgi.ini.tmp {uwsgi_conf_file}'
             .format(**env), pty=True)


@task
def upload_nginx_conf():
    require('nginx_conf_file', 'host', provided_by=envs.ENVS)
    nginx_file = 'nginx/nginx-{host}.conf'.format(**env)

    check_file(nginx_file)

    put(nginx_file, '{project_path}/conf/nginx.conf.tmp'.format(**env))
    with cd(env.project_path):
        sudo('chown root:root conf/nginx.conf.tmp')
        sudo('chmod 644 conf/nginx.conf.tmp')
        sudo('mv -f conf/nginx.conf.tmp {nginx_conf_file}'.format(**env),
             pty=True)


@task
def install_systemd_services():
    require('host', 'project_path', provided_by=envs.ENVS)

    units = [
        'api.service',
        'renderer.service',
        'markup-renderer.service',
        '.target'
    ]

    for unit in units:
        unit_file = '{}.{}'.format(env.host, unit)
        local_conf = 'systemd/{}'.format(unit_file)
        check_file(local_conf)
        put(local_conf, '{}/conf/{}.tmp'.format(env.project_path, unit_file))
        with cd(os.path.join(env.project_path, 'conf')):
            sudo('chown root:root {}.tmp'.format(unit_file))
            sudo('chmod 644 {}.tmp'.format(unit_file))
            sudo('mv -f {0}.tmp /etc/systemd/system/{0}'.format(unit_file))

    make_uwsgi_run_dir()
    sudo('systemctl daemon-reload')


@task
def remove_systemd_services():
    units = [
        'api.service',
        'renderer.service',
        'markup-renderer.service',
        '.target'
    ]

    for unit in units:
        sudo('rm -f /etc/systemd/system/{}.{}'.format(env.host, unit))

    sudo('systemctl daemon-reload')


@task
def restart_all_services():
    require('host', provided_by=envs.ENVS)
    make_uwsgi_run_dir()
    sudo('systemctl restart {}.target nginx.service'.format(env.host))


def make_uwsgi_run_dir():
    require('host', 'uwsgi_socket_gid', 'uwsgi_socket_uid',
            provided_by=envs.ENVS)
    sudo('mkdir -p /run/uwsgi')
    sudo('chown {uwsgi_socket_gid}:{uwsgi_socket_uid} /run/uwsgi'.format(
        **env))


def check_file(filename):
    if not os.path.exists(filename):
        abort(red('Missing config file for {} at {}'.format(
            env.host, filename)))


def make_release_folders(dirname):
    """
    Setup folders for each subproject.

      * logs: Logs for long-running process
      * releases: Code for release currently being run
      * packages: tarballs for the folders in releases
    """
    require('hosts', 'project_path', provided_by=envs.ENVS)
    with cd(env.project_path):
        with cd(dirname):
            run('mkdir -p logs releases packages')
            with cd('releases'):
                run('touch none')
                run('test ! -e current && ln -s none current', quiet=True)
                run('test ! -e previous && ln -s none previous', quiet=True)


@task
def full_deploy(api_version='HEAD', renderer_version='HEAD',
                markup_renderer_version=None):
    """
    Deploy the site, migrate the database, and open in a web browser.
    """
    setup()

    api.full_deploy(api_version)
    renderer.full_deploy(renderer_version)
    markup_renderer.full_deploy(markup_renderer_version)

    upload_nginx_conf()
    upload_uwsgi_conf()
    install_systemd_services()


@task
def full_deploy_with_restart(api_version='HEAD', renderer_version='HEAD',
                             markup_renderer_version=None):
    full_deploy(api_version, renderer_version)
    restart_all_services()

    time.sleep(2)
    local('rmdir --ignore-fail-on-non-empty {TMP_DIR}'.format(**env))
    local('{} http://{}/'.format(
        'xdg-open' if 'linux' in sys.platform else 'open', env.host))
