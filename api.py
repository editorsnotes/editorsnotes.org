import os

from fabric.api import *

from envs import ENVS
import utils


@task
def full_deploy(version='HEAD'):
    "Upload the release, install dependencies, and run configuration steps"
    upload_release(version)
    install_deps()
    deploy()


@task
def upload_release(version='HEAD'):
    utils.upload_release('api', version)
    utils.symlink_current_release('api')


@task
def install_deps():
    make_virtual_env()
    install_requirements()


@task
def make_virtual_env():
    with cd(env.project_path):
        with cd('api'):
            run('virtualenv -p {python} --no-site-packages ./venv/'.format(**env))


@task
def deploy():
    """
    Deploy the latest version of the API.

    Download the newest version of editorsnotes, install requirements in the
    virtualenv, upload the virtual host, and restart the webserver.
    """
    require('hosts', 'project_path', provided_by=ENVS)
    upload_local_settings()
    install_wsgi()
    migrate()
    collect_static()


@task
def test():
    "Run the test suite remotely."
    require('hosts', 'project_path', provided_by=ENVS)
    with cd('{project_path}/api/releases/current'.format(**env)):
        run('../../venv/bin/python manage.py test')


@task
def migrate():
    "Update the database for the current release"
    require('hosts', 'project_path', provided_by=ENVS)
    with cd('{project_path}/api/releases/current'.format(**env)):
        run('../../venv/bin/python manage.py migrate --noinput')


def install_wsgi():
    "Install the wsgi file for the current release"
    put('django.wsgi', '{project_path}/api/releases/current/wsgi.py'.format(**env))



def upload_local_settings():
    "Upload the appropriate local settings file."
    require('host', provided_by=ENVS)
    settings_file = 'settings/settings-{host}.py'.format(**env)
    if not os.path.exists(settings_file):
        abort(red('Put the settings for {} at {}'.format(
            env.host, settings_file)))
    put(settings_file,
        os.path.join(env.project_path, 'api', 'releases', 'current',
                     env.project_name, 'settings_local.py'))


def get_deploy_info(version):
    with lcd(os.getenv('EDITORSNOTES_GIT')):
        release = local('git rev-parse {}'.format(version), capture=True)

        current_tag = local('git describe --tags --exact-match {} '
                            '2> /dev/null || true'.format(release),
                            capture=True)
        if current_tag:
            release = current_tag

        github_repo = local(
            'git remote --verbose | '
            'grep -o "git@github.com.* (push)" | '
            'head -n 1 | '
            "sed -r -e 's/git@github.com:([^ ]+)\.git.*/\\1/'",
            capture=True)
    url = github_repo and 'http://github.com/{}/tree/{}'.format(github_repo,
                                                                release)
    return release, url


def upload_deploy_info(version):
    "Upload information about the version and time of deployment."
    require('release', provided_by=ENVS)

    version_file = os.path.join(env.TMP_DIR, 'version.txt')
    version_url_file = os.path.join(env.TMP_DIR, 'version-url.txt')
    time_file = os.path.join(env.TMP_DIR, 'time-deployed.txt')

    with lcd(os.getenv('EDITORSNOTES_GIT')), open(version_file, 'wb') as f:
        call(['git', 'rev-parse', version], stdout=f)

    release, url = get_deploy_info(version)
    with open(version_file, 'wb') as f:
        f.write(release)
    with open(version_url_file, 'wb') as f:
        f.write(url)
    with open(time_file, 'wb') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M'))

    dest = '{project_path}/api/releases/{release}'.format(**env)
    put(version_file, dest)
    put(version_url_file, dest)
    put(time_file, dest)
    local('rm {}'.format(version_file))
    local('rm {}'.format(version_url_file))
    local('rm {}'.format(time_file))


def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=ENVS)
    with cd('{project_path}/api'.format(**env)):
        run('./venv/bin/pip install -r '
            './releases/current/requirements.txt'.format(**env))


def collect_static():
    "Collect static files"
    require('hosts', 'project_path', provided_by=ENVS)
    with cd('{project_path}/releases/current'.format(**env)):
        run('../../bin/python manage.py collectstatic --noinput')
