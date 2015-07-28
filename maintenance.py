from fabric.api import *

from envs import ENVS

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
    
