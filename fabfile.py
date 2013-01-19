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
env.release = time.strftime('%Y%m%d%H%M%S')
env.TMP_DIR = os.path.join(os.path.dirname(env.real_fabfile), 'tmp')

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
    if not os.getenv('EDITORSNOTES_GIT'):
        abort(red('Create environment variable EDITORSNOTES_GIT containing a path to your editorsnotes git repository.'))
    local('mkdir -p {}'.format(env.TMP_DIR))
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
        'xdg-open' if 'linux' in sys.platform else 'open', env.host))
    local('rmdir --ignore-fail-on-non-empty {TMP_DIR}'.format(**env))
    
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
    require('project_path', 'release', provided_by=ENVS)
    with lcd(os.getenv('EDITORSNOTES_GIT')):
        local('git archive --format=tar HEAD | gzip > {TMP_DIR}/{release}.tar.gz'.format(**env))
    run('mkdir -p {project_path}/releases/{release}'.format(**env))
    put('{TMP_DIR}/{release}.tar.gz'.format(**env),
        '{project_path}/packages/'.format(**env))
    with cd('{project_path}/releases/{release}'.format(**env)):
        run('tar zxf ../../packages/{release}.tar.gz'.format(**env))
    local('rm {TMP_DIR}/{release}.tar.gz'.format(**env))

def upload_local_settings():
    "Upload the appropriate local settings file."
    require('host', 'release', provided_by=ENVS)
    settings_file = 'settings/settings-{host}.py'.format(**env)
    if not os.path.exists(settings_file):
        abort(red('Put the settings for {} at {}'.format(
            env.host, settings_file)))
    put(settings_file,
        '{project_path}/releases/{release}/{project_name}/settings_local.py'.format(**env))

def upload_deploy_info():
    "Upload information about the version and time of deployment."
    require('release', provided_by=ENVS)

    version_file = os.path.join(env.TMP_DIR, 'version.txt')
    time_file = os.path.join(env.TMP_DIR, 'time-deployed.txt')

    with lcd(os.getenv('EDITORSNOTES_GIT')), open(version_file, 'wb') as f:
        call(['git', 'rev-parse', 'HEAD'], stdout=f)

    with open(time_file, 'wb') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M'))

    dest = '{project_path}/releases/{release}/{project_name}/templates'.format(**env)
    put(version_file, dest)
    put(time_file, dest)
    local('rm {}'.format(version_file))
    local('rm {}'.format(time_file))

def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=ENVS)
    with cd('{project_path}'.format(**env)):
        run('./bin/pip install -r ./releases/{release}/requirements.txt'.format(**env))

def symlink_system_packages():
    "Create symlinks to system site-packages."
    require('python', 'project_path', provided_by=ENVS)
    missing = []
    req_file = os.path.join(os.getenv('EDITORSNOTES_GIT'), 'requirements.txt')
    requirements = (
        req.rstrip().replace('# symlink: ', '')
        for req in open(req_file, 'r')
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
    vhost_file = 'vhosts/vhost-{host}.conf'.format(**env)
    if not os.path.exists(vhost_file):
        abort(red('Put the vhost config for {} at {}'.format(
            env.host, vhost_file)))
    put('django.wsgi', '{project_path}/releases/{release}'.format(**env))
    put(vhost_file, '{project_path}/vhost-{host}.conf.tmp'.format(**env))
    with cd(env.project_path):
        sudo('mv -f vhost-{host}.conf.tmp {vhosts_path}/vhost-{host}.conf'.format(
            **env), pty=True)

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
    with cd('{project_path}/releases/current'.format(**env)):
        run('../../bin/python manage.py collectstatic --noinput')
    
def restart_webserver():
    "Restart the web server."
    sudo('apachectl restart', pty=True)
