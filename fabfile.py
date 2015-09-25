# -*- coding: utf-8 -*-

from fabric.api import *
from fabric.colors import red
from fabric.contrib.files import exists

import os
import sys
import time


# Namespaced fabric tasks
import envs
import api
import renderer
import maintenance


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
def setup():
    """
    Setup all project directories.
    """
    require('hosts', 'project_path', provided_by=envs.ENVS)
    run('mkdir -p {project_path}'.format(**env))
    with cd(env.project_path):
        run('mkdir -p api renderer lib conf')
        run('mkdir -p api/static api/uploads')

        make_release_folders('api')
        make_release_folders('renderer')

@task
def upload_nginx_conf():
    require('nginx_conf_path', provided_by=envs.ENVS)
    nginx_file = 'nginx/nginx-{host}.conf'.format(**env)
    if not os.path.exists(nginx_file):
        abort(red('Put the nginx config for {} at {}'.format(
            env.host, nginx_file)))
    put(nginx_file, '{project_path}/confs/nginx.conf.tmp'.format(**env))
    with cd(env.project_path):
        sudo('mv -f confs/nginx.conf.tmp '
             '{nginx_conf_path}/{project_name}.conf'.format(**env), pty=True)

@task
def restart_nginx():
    sudo('systemctl restart nginx.server', pty=True)


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
def full_deploy(api_version='HEAD', renderer_version='HEAD'):
    """
    Deploy the site, migrate the database, and open in a web browser.
    """
    install_iojs()

    api.full_deploy(api_version)
    renderer.full_deploy(renderer_version)

    upload_nginx_conf()
    restart_nginx()

    time.sleep(2)

    local('rmdir --ignore-fail-on-non-empty {TMP_DIR}'.format(**env))
    local('{} http://{}/'.format(
        'xdg-open' if 'linux' in sys.platform else 'open', env.host))


@task
def install_iojs():
    IOJS_VERSION = 'v2.4.0'
    PLATFORM = '64' if run('uname -m', quiet=True).endswith('64') else '86'
    pkg = 'iojs-{}-linux-x{}'.format(IOJS_VERSION, PLATFORM)
    tarball = 'https://iojs.org/dist/{}/{}.tar.xz'.format(IOJS_VERSION, pkg)

    if exists('{}/lib/{}'.format(env.project_path, pkg)):
        print 'io.js {} already installed'.format(IOJS_VERSION)
    else:
        with cd(os.path.join(env.project_path, 'lib')):
            run('wget {}'.format(tarball))
            run('rm -f ./iojs-current')
            run('tar xJf {0}.tar.xz && rm {0}.tar.xz'.format(pkg))
            run('ln -fs {} iojs-current'.format(pkg))
