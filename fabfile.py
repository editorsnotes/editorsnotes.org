# -*- coding: utf-8 -*-

from fabric.api import *
from fabric.colors import red, green
from fabric.contrib.console import confirm
from fabric.contrib.files import exists
from fabric.context_managers import path
from datetime import datetime
from subprocess import call
import os
import sys
import time


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

import envs
import api
import renderer


#########
# Tasks #
#########
@task
def test_remote():
    "Run the test suite remotely."
    require('hosts', 'project_path', provided_by=envs.ENVS)
    with cd('{project_path}/releases/current'.format(**env)):
        run('../../bin/python manage.py test')
    
@task
def setup():
    """
    Setup a new virtualenv & create project dirs, then run a full deployment.
    """
    require('hosts', 'project_path', provided_by=envs.ENVS)
    run('mkdir -p {project_path}'.format(**env))
    with cd(env.project_path):
        run('mkdir -p api renderer')
        with cd('api'):
            run('virtualenv -p {python} --no-site-packages .'.format(**env))
            run('mkdir -p logs releases shared packages')
            run('cd releases; touch none; ln -sf none current; ln -sf none previous')

@task
def full_deploy(version='HEAD'):
    """
    Deploy the site, migrate the database, and open in a web browser.
    """
    deploy_api(version)
    migrate()
    time.sleep(2)
    local('rmdir --ignore-fail-on-non-empty {TMP_DIR}'.format(**env))
    local('{} http://{}/'.format(
        'xdg-open' if 'linux' in sys.platform else 'open', env.host))
    


MAINTENANCE_TEXT = """
<!doctype html>
<html>
  <head><title>Editors' Notes: Down for maintenance</title></head>
  <body>
    <p>Editors' Notes is down for maintenance, but will return soon.</p>
  </body>
</html>
"""
@task
def take_offline():
    "Take the site down for maintanence, redirecting all requests to a notification."
    require('project_path', provided_by=envs.ENVS)
    maintenance_file_path = '{TMP_DIR}/offline.html'.format(**env)
    with open(maintenance_file_path, 'w') as outfile:
        outfile.write(MAINTENANCE_TEXT)
    put(maintenance_file_path, env.project_path)
    local('rm {}'.format(maintenance_file_path))
    local('rmdir --ignore-fail-on-non-empty {TMP_DIR}'.format(**env))
    restart_webserver()

@task
def put_back_online():
    require('project_path', provided_by=envs.ENVS)
    maintenance_file_path = '{project_path}/offline.html'.format(**env)
    if exists(maintenance_file_path):
        run('rm {}'.format(maintenance_file_path))
        restart_webserver()
    

###########
# Helpers #
###########
def install_nodejs():
    NODE_VERSION = 'v0.10.28'
    PLATFORM = '64' if run('uname -m', quiet=True).endswith('64') else '86'
    pkg = 'node-{}-linux-x{}'.format(NODE_VERSION, PLATFORM)
    tarball = 'http://nodejs.org/dist/{}/{}.tar.gz'.format(NODE_VERSION, pkg)

    if exists('{}/lib/{}'.format(env.project_path, pkg)):
        print 'node.js {} already installed'.format(NODE_VERSION)
    else:
        with cd(os.path.join(env.project_path, 'lib')):
            run('wget {}'.format(tarball))
            run('rm -f ./node')
            run('tar xzf {0}.tar.gz && rm {0}.tar.gz'.format(pkg))
            run('ln -fs {} node'.format(pkg))

    with cd(os.path.join(env.project_path, 'lib')):
        run('cp ../releases/current/package.json .')
        run('./node/bin/npm install')
        run('rm package.json')
        run('./node/bin/npm install -g jsmin')
