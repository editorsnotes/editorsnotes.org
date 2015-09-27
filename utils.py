from fabric.api import *
from fabric.colors import red, green
from fabric.contrib.console import confirm

from envs import ENVS


def confirm_subproject(subproject):
    if subproject not in env.git:
        abort(red(
            'No such project: {}.\n\nKnown projects are: {}'.format(
                project, env.git.keys().join(','))
        ))


def symlink_current_release(project):
    "Symlink our current release."
    require('release', provided_by=ENVS)

    confirm_subproject(project)

    with cd(env.project_path):
        with cd(project):
            run('rm releases/previous; mv releases/current releases/previous;')
            run('ln -s {release} releases/current'.format(**env))


def upload_release(project, version='HEAD'):
    require('hosts', 'project_path', provided_by=ENVS)

    confirm_subproject(project)

    git_dir = env.git[project]

    if version != 'HEAD':
        ensure_branch_exists(version, git_dir)

    deployment_src_str = (
        'git branch/tag `{}` of git repository {}'.format(version, git_dir)
        if version != 'HEAD'
        else 'HEAD of local git repository ({})'.format(git_dir))

    print green('\nAbout to deploy {} to {}'.format(
        deployment_src_str, '|'.join(env.hosts)))

    msg = 'Continue?'
    if not confirm(msg, default=False):
        return

    local('mkdir -p {}'.format(env.TMP_DIR))
    upload_tar_from_git(project, git_dir, version)


def ensure_branch_exists(branch, git_dir):
    with lcd(git_dir):
        with warn_only():
            show_ref = local('git show-ref --heads --tags {}'.format(branch),
                             capture=True)
    if not show_ref:
        abort(red('Could not find local head or tag `{}` '
                  'in git repository {}. '
                  'Do you need to fetch it first?'.format(branch, git_dir)))


def upload_tar_from_git(project, git_dir, version):
    "Create an archive from the current Git branch and upload it."
    require('project_path', 'release', provided_by=ENVS)
    with lcd(git_dir):
        local('git archive --format=tar {_version} | '
              'gzip > {TMP_DIR}/{release}.tar.gz'.format(
                  _version=version, **env))
    run('mkdir -p {project_path}/{subdir}/releases/{release}'.format(
        subdir=project, **env))
    put('{TMP_DIR}/{release}.tar.gz'.format(**env),
        '{project_path}/{subdir}/packages/'.format(subdir=project, **env))
    with cd('{project_path}/{subdir}/releases/{release}'.format(subdir=project,
                                                                **env)):
        run('tar zxf ../../packages/{release}.tar.gz'.format(**env))
    local('rm {TMP_DIR}/{release}.tar.gz'.format(**env))
