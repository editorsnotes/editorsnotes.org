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
def deploy(version='HEAD'):
    """
    Deploy the latest version of the site.

    Download the newest version of editorsnotes, install requirements in the
    virtualenv, upload the virtual host, and restart the webserver.
    """
    require('hosts', 'project_path', provided_by=ENVS)
    if not os.getenv('EDITORSNOTES_GIT'):
        abort(red('Create environment variable EDITORSNOTES_GIT containing a path to your editorsnotes git repository.'))

    git_dir = os.getenv('EDITORSNOTES_GIT')
    if version != 'HEAD':
        ensure_branch_exists(version, git_dir)

    deployment_src = (
        'git branch/tag `{}`'.format(version)
        if version != 'HEAD'
        else 'HEAD of local git repository ({})'.format(git_dir))
    print green('\nAbout to deploy {} to {}'.format(deployment_src,
                                                    '|'.join(env.hosts)))

    msg = 'Continue?'
    if not confirm(msg, default=False):
        return

    local('mkdir -p {}'.format(env.TMP_DIR))
    upload_tar_from_git(version)
    upload_local_settings()
    upload_deploy_info()
    install_requirements()
    symlink_system_packages()
    install_vhosts()
    install_wsgi()
    symlink_current_release()
    install_nodejs()
    collect_static()
    restart_webserver()

@task
def full_deploy(version='HEAD'):
    """
    Deploy the site, migrate the database, and open in a web browser.
    """
    deploy(version)
    migrate()
    time.sleep(2)
    local('rmdir --ignore-fail-on-non-empty {TMP_DIR}'.format(**env))
    local('{} http://{}/'.format(
        'xdg-open' if 'linux' in sys.platform else 'open', env.host))
    
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

@task
def install_vhosts():
    "Add the virtualhost file to apache."
    require('release', provided_by=ENVS)
    vhost_file = 'vhosts/vhost-{host}.conf'.format(**env)
    if not os.path.exists(vhost_file):
        abort(red('Put the vhost config for {} at {}'.format(
            env.host, vhost_file)))
    put(vhost_file, '{project_path}/vhost-{host}.conf.tmp'.format(**env))
    with cd(env.project_path):
        sudo('mv -f vhost-{host}.conf.tmp {vhosts_path}/vhost-{host}.conf'.format(
            **env), pty=True)

def install_wsgi():
    put('django.wsgi', '{project_path}/releases/{release}'.format(**env))



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
    require('project_path', provided_by=ENVS)
    maintenance_file_path = '{TMP_DIR}/offline.html'.format(**env)
    with open(maintenance_file_path, 'w') as outfile:
        outfile.write(MAINTENANCE_TEXT)
    put(maintenance_file_path, env.project_path)
    local('rm {}'.format(maintenance_file_path))
    local('rmdir --ignore-fail-on-non-empty {TMP_DIR}'.format(**env))
    restart_webserver()

@task
def put_back_online():
    require('project_path', provided_by=ENVS)
    maintenance_file_path = '{project_path}/offline.html'.format(**env)
    if exists(maintenance_file_path):
        run('rm {}'.format(maintenance_file_path))
        restart_webserver()
    

###########
# Helpers #
###########
def ensure_branch_exists(branch, git_dir):
    with lcd(git_dir):
        with warn_only():
            show_ref = local('git show-ref --heads --tags {}'.format(branch), capture=True)
    if not show_ref:
        abort(red('Could not find local head or tag `{}`. '
                  'Do you need to fetch it first?'.format(branch)))

def upload_tar_from_git(version='HEAD'):
    "Create an archive from the current Git branch and upload it."
    require('project_path', 'release', provided_by=ENVS)
    with lcd(os.getenv('EDITORSNOTES_GIT')):
        local('git archive --format=tar {_version} | '
              'gzip > {TMP_DIR}/{release}.tar.gz'.format(
                  _version=version, **env))
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

def get_deploy_info():
    with lcd(os.getenv('EDITORSNOTES_GIT')):
        current_tag = local('git describe --tags --exact-match 2> /dev/null || true',
                            capture=True)
        if current_tag:
            release = current_tag
        else:
            release = local('git rev-parse HEAD', capture=True)
        github_repo = local('git remote --verbose | '
                            'grep -o "git@github.com.* (push)" | '
                            'head -n 1 | '
                            "sed -r -e 's/git@github.com:([^ ]+)\.git.*/\\1/'",
                        capture=True)
    url = github_repo and 'http://github.com/{}/tree/{}'.format(github_repo, release)
    return release, url

def upload_deploy_info():
    "Upload information about the version and time of deployment."
    require('release', provided_by=ENVS)

    version_file = os.path.join(env.TMP_DIR, 'version.txt')
    version_url_file = os.path.join(env.TMP_DIR, 'version-url.txt')
    time_file = os.path.join(env.TMP_DIR, 'time-deployed.txt')

    with lcd(os.getenv('EDITORSNOTES_GIT')), open(version_file, 'wb') as f:
        call(['git', 'rev-parse', 'HEAD'], stdout=f)

    release, url = get_deploy_info()
    with open(version_file, 'wb') as f:
        f.write(release)
    with open(version_url_file, 'wb') as f:
        f.write(url)
    with open(time_file, 'wb') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M'))

    dest = '{project_path}/releases/{release}/{project_name}/templates'.format(**env)
    put(version_file, dest)
    put(version_url_file, dest)
    put(time_file, dest)
    local('rm {}'.format(version_file))
    local('rm {}'.format(version_url_file))
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

def symlink_current_release():
    "Symlink our current release."
    require('release', provided_by=ENVS)
    with cd(env.project_path):
        run('rm releases/previous; mv releases/current releases/previous;')
        run('ln -s {release} releases/current'.format(**env))
    
@task
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
        run('ln -s ../../lib/node_modules .')
        with path('../../lib/node/bin', behavior='prepend'):
            run('../../bin/python manage.py compile_browserify')

@task
def restart_webserver():
    "Restart the web server."
    sudo('apachectl restart', pty=True)
