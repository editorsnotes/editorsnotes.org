import os

from fabric.api import *

import utils
from envs import ENVS


@task
def upload_release(version='HEAD'):
    utils.upload_release('renderer', version)
    utils.symlink_current_release('renderer')


@task
def install_deps():
    require('hosts', 'project_path', provided_by=ENVS)
    with cd(os.path.join(env.project_path, 'renderer', 'releases', 'current')):
        run('../../../lib/iojs-current/bin/npm install')


@task
def full_deploy(version='HEAD'):
    upload_release(version)
    install_deps()
    deploy()


@task
def deploy():
    compile_application()


@task
def compile_application():
    require('hosts', 'project_path', provided_by=ENVS)
    with cd(os.path.join(env.project_path, 'renderer', 'releases', 'current')):
        run('make')
