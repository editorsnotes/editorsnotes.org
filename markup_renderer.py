import os

from fabric.api import *

from envs import ENVS


def install_renderer(version=None):
    require('project_path', provided_by=ENVS)
    with cd(os.path.join(env.project_path, 'markup_renderer')):
        run('mkdir -p node_modules')

        package = 'editorsnotes-markup-renderer'
        run('npm uninstall {} --silent'.format(package))

        if (version):
            package += '@{}'.format(version)

        run('npm install {}'.format(package))


@task
def full_deploy(version='HEAD'):
    install_renderer()
