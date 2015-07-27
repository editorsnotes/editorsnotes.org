from fabric.api import *

from envs import ENVS


@task
def deploy(version='HEAD'):
    """
    Deploy the latest version of the API.

    Download the newest version of editorsnotes, install requirements in the
    virtualenv, upload the virtual host, and restart the webserver.
    """
    require('hosts', 'project_path', provided_by=ENVS)

    git_dir = os.getenv('EDITORSNOTES_API_GIT')
    if not git_dir:
        abort(red(
            'Create environment variable EDITORSNOTES_GIT containing a path '
            'to your editorsnotes git repository.'
        ))

    if version != 'HEAD':
        ensure_branch_exists(version, git_dir)

    deployment_src_str = (
        'git branch/tag `{}`'.format(version)
        if version != 'HEAD'
        else 'HEAD of local git repository ({})'.format(git_dir))

    print green('\nAbout to deploy {} to {}'.format(
        deployment_src_str, '|'.join(env.hosts)))

    msg = 'Continue?'
    if not confirm(msg, default=False):
        return

    local('mkdir -p {}'.format(env.TMP_DIR))
    upload_tar_from_git(version)
    upload_local_settings()
    upload_deploy_info(version)
    install_requirements()
    # install_vhosts()
    # install_wsgi()
    symlink_current_release()
    # install_nodejs()
    # collect_static()
    # restart_webserver()

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

@task
def migrate():
    "Update the database"
    require('hosts', 'project_path', provided_by=ENVS)
    with cd('{project_path}/releases/current'.format(**env)):
        run('../../bin/python manage.py migrate --noinput')

@task
def restart_webserver():
    "Restart the web server."
    sudo('apachectl restart', pty=True)


def install_wsgi():
    put('django.wsgi', '{project_path}/releases/{release}'.format(**env))


def ensure_branch_exists(branch, git_dir):
    with lcd(git_dir):
        with warn_only():
            show_ref = local('git show-ref --heads --tags {}'.format(branch),
                             capture=True)
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
    run('mkdir -p {project_path}/api/releases/{release}'.format(**env))
    put('{TMP_DIR}/{release}.tar.gz'.format(**env),
        '{project_path}/api/packages/'.format(**env))
    with cd('{project_path}/api/releases/{release}'.format(**env)):
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
        os.path.join(env.project_path, 'api', 'releases', env.release,
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
        run('./bin/pip install -r '
            './releases/{release}/requirements.txt'.format(**env))


def symlink_current_release():
    "Symlink our current release."
    require('release', provided_by=ENVS)
    with cd(env.project_path):
        with cd('api'):
            run('rm releases/previous; mv releases/current releases/previous;')
            run('ln -s {release} releases/current'.format(**env))

def collect_static():
    "Collect static files"
    require('hosts', 'project_path', provided_by=ENVS)
    with cd('{project_path}/releases/current'.format(**env)):
        run('../../bin/python manage.py collectstatic --noinput')
