# -*- coding: utf-8 -*-

from fabric.api import *
from fabric.colors import red
from fabric.contrib.console import confirm
from datetime import datetime
from subprocess import call
import os
import sys
import time

#################
# Local fabfile #
#################
try:
    from fabfile_local import *
except ImportError:
    pass


################
# Environments #
################
env.project_name = 'editorsnotes'

@task
def beta():
    "Use the beta-testing webserver."
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

# Create custom environments in fabfile_local.py, in the same style as above
ENVS = [beta, pro, 'Custom host defined in fabfile_local.py']


#########
# Tasks #
#########
@task
def test_remote():
    "Run the test suite remotely."
    require('hosts', 'project_path', provided_by=ENVS)
    with cd('{project_path}/releases/current'.format(**env)):
        run('../../bin/python manage.py test')
    
@task
def setup():
    """
    Setup a new virtualenv & create project dirs, then run a full deployment.
    """
    require('hosts', 'project_path', provided_by=ENVS)
    run('mkdir -p {project_path}'.format(**env))
    with cd(env.project_path):
        run('virtualenv -p {python} --no-site-packages .'.format(**env))
        run('mkdir -p logs releases shared packages')
        run('cd releases; touch none; ln -sf none current; ln -sf none previous')
    deploy()
    
@task
def deploy():
    """
    Deploy the latest version of the site.

    Download the newest version of editorsnotes, install requirements in the
    virtualenv, upload the virtual host, and restart the webserver.
    """
    require('hosts', 'project_path', provided_by=ENVS)
    env.release = time.strftime('%Y%m%d%H%M%S')
    if not os.getenv('EDITORSNOTES_GIT'):
        abort(red('Create environment variable EDITORSNOTES_GIT containing a path to your editorsnotes git repository.'))
    upload_tar_from_git()
    upload_local_settings()
    upload_deploy_info()
    symlink_system_packages()
    install_requirements()
    install_site()
    symlink_current_release()
    migrate()
    collect_static()
    restart_webserver()
    time.sleep(2)
    local('{} http://{}/'.format(
        'xdg-open' if 'linux' in sys.platform else 'open', env['host']))
    
@task
def deploy_version(version):
    "Specify a specific version to be made live."
    require('hosts', 'project_path', provided_by=ENVS)
    env.version = version
    with cd(env.project_path):
        run('rm releases/previous; mv releases/current releases/previous')
        run('ln -s {version} releases/current'.format(**env))
    restart_webserver()
    
@task
def rollback():
    """
    Load the previously current version of the code.

    Limited rollback capability. Simply loads the previously current
    version of the code. Rolling back again will swap between the two.
    """
    require('hosts', 'project_path', provided_by=ENVS)
    with cd(env.project_path):
        run('mv releases/current releases/_previous;')
        run('mv releases/previous releases/current;')
        run('mv releases/_previous releases/previous;')
    restart_webserver()

@task
def clean():
    "Clean out old packages and releases."
    require('hosts', 'project_path', provided_by=ENVS)
    msg = 'Are you sure you want to delete everything on {host}?'
    if not confirm(msg.format(**env), default=False):
        return
    with cd(env.project_path):
        run('rm -rf packages; rm -rf releases')
        run('mkdir -p packages; mkdir -p releases')
        run('cd releases; touch none; ln -sf none current; ln -sf none previous')
    

###########
# Helpers #
###########
def upload_tar_from_git():
    "Create an archive from the current Git branch and upload it."
    require('release', provided_by=ENVS)
    local('git archive --format=tar HEAD | gzip > %(release)s.tar.gz' % env)
    run('mkdir -p %(project_path)s/releases/%(release)s' % env)
    put('%(release)s.tar.gz' % env, '%(project_path)s/packages/' % env)
    run('cd %(project_path)s/releases/%(release)s && tar zxf ../../packages/%(release)s.tar.gz' % env)
    local('rm %(release)s.tar.gz' % env)

def upload_local_settings():
    "Upload the appropriate local settings file."
    require('release', provided_by=ENVS)
    put('deploy/settings-{host}.py'.format(**env), 
        '{project_path}/releases/{release}/{project_name}/settings_local.py'.format(**env))

def upload_deploy_info():
    "Upload information about the version and time of deployment."
    require('release', provided_by=ENVS)
    with open('%(project_name)s/templates/version.txt' % env, 'wb') as f:
        call(['git', 'rev-parse', 'HEAD'], stdout=f)
    with open('%(project_name)s/templates/time-deployed.txt' % env, 'wb') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M'))
    for filename in ['version.txt', 'time-deployed.txt']:
        put(('%(project_name)s/templates/' % env) + filename,
            ('%(project_path)s/releases/%(release)s/%(project_name)s/templates/' % env) + filename)

def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=ENVS)
    run('export SAVED_PIP_VIRTUALENV_BASE=$PIP_VIRTUALENV_BASE; unset PIP_VIRTUALENV_BASE; ' +
        'cd %(project_path)s; ./bin/pip install -E . -r ./releases/%(release)s/requirements.txt; ' % env +
        'export PIP_VIRTUALENV_BASE=$SAVED_PIP_VIRTUALENV_BASE; unset SAVED_PIP_VIRTUALENV_BASE')

def symlink_system_packages():
    "Create symlinks to system site-packages."
    require('python', 'project_path', provided_by=ENVS)
    missing = []
    requirements = (
        req.rstrip().replace('# symlink: ', '')
        for req in open('requirements.txt', 'r')
        if req.startswith('# symlink: ')
    )
    for req in requirements:
        cmd = '{0} -c "import os, {1}; print os.path.dirname({1}.__file__)"'
        req_file = run(cmd.format(env.python, req), warn_only=True, quiet=True)
        if req_file.failed:
            missing.append(req)
            continue
        with cd(os.path.join(env.project_path, 'lib', 'python2.7', 'site-packages')):
            run('ln -f -s {}'.format(req_file))
    if missing:
        abort(red('Missing python packages: {}'.format(', '.join(missing))))

def install_site():
    "Add the virtualhost file to apache."
    require('release', provided_by=ENVS)
    put('deploy/vhost-{host}.conf'.format(**env),
        '{project_path}/vhost-{host}.conf.tmp'.format(**env))
    with cd(env['project_path']):
        sudo(('mv -f vhost-{host}.conf.tmp '
              '{vhosts_path}/vhost-{host}.conf').format(**env), pty=True)

def symlink_current_release():
    "Symlink our current release."
    require('release', provided_by=ENVS)
    with cd(env.project_path):
        run('rm releases/previous; mv releases/current releases/previous;')
        run('ln -s {release} releases/current'.format(**env))
    
def migrate():
    "Update the database"
    require('hosts', 'project_path', provided_by=ENVS)
    with cd('{project_path}/releases/current'.format(**env)):
        run('../../bin/python manage.py syncdb --noinput')
        run('../../bin/python manage.py migrate --noinput')

def collect_static():
    "Collect static files"
    require('hosts', 'project_path', provided_by=ENVS)
    with cd('{project_path}/releases/current' % env):
        run('../../bin/python manage.py collectstatic --noinput')
    
def restart_webserver():
    "Restart the web server."
    sudo('apachectl restart', pty=True)
