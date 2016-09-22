from fabric.api import env, local, run, task, settings, abort, put, cd, prefix, get, sudo, shell_env, open_shell, prompt
from fabric.colors import red, green, yellow, white
from fabric.context_managers import hide
from fabric.contrib.project import rsync_project
import dotenv
import random
import string

import os
import sys
from distutils.spawn import find_executable
import logging
import re
import posixpath


def set_env(system):

    if system == 'production':
        env.local_dotenv_path = os.path.join(os.path.dirname(__file__), './.production.env')
        dotenv.load_dotenv(env.local_dotenv_path)
        env.project_name = os.environ.get('PROJECT_NAME', '')
        env.project_dir = posixpath.join('/srv/apps/', env.project_name)
        env.is_local = False

    if system == 'staging':
        env.local_dotenv_path = os.path.join(os.path.dirname(__file__), './.staging.env')
        dotenv.load_dotenv(env.local_dotenv_path)
        env.project_name = os.environ.get('PROJECT_NAME', '')
        env.project_dir = posixpath.join('/srv/apps/', env.project_name)
        env.is_local = False

    elif system == 'local':
        env.local_dotenv_path = os.path.join(os.path.dirname(__file__), './.local.env')
        dotenv.load_dotenv(env.local_dotenv_path)
        env.project_name = os.environ.get('PROJECT_NAME', '')
        env.project_dir = './'
        env.is_local = True

    env.use_ssh_config = True
    env.env_file = os.environ.get('ENV_FILE', '')

    # Bug: when setting this inside a function. Using host_string as workaround
    env.hosts = [os.environ.get('HOST_NAME', ''), ]
    env.host_string = os.environ.get('HOST_NAME', '')

    env.virtual_host = os.environ.get('VIRTUAL_HOST', '')
    env.image_name = os.environ.get('IMAGE_NAME', '')
    env.build_dir = '/srv/build'

    env.virtual_env = os.environ.get('VIRTUAL_ENV', '')

    activate = {
        'posix': 'source activate %s' % env.virtual_env,
        'nt': 'activate %s' % env.virtual_env,
    }
    env.os = os.name
    env.activate = activate[env.os]

    env.postgres_data = '/var/lib/postgresql/data'

    env.project_path = os.path.dirname(os.path.dirname(__file__))

    env.log_level = logging.DEBUG


def L():
    set_env('local')


def P():
    set_env('production')


def S():
    set_env('staging')

# sets path and execute on local or remote server:
def execute(cmd, path=''):
    # Set path:
    if not path:
        path = env.project_dir

    # Execute:
    with cd(path):
        local(cmd) if env.is_local else run(cmd)


def compose(cmd='--help', path=''):
    template = {
        'posix': 'docker-compose {cmd}'
    }

    try:
        execute(cmd=template[env.os].format(cmd=cmd), path=path)
    except SystemExit:
        if env.is_local:
            check_default_machine()


def docker(cmd='--help'):
    template = 'docker {cmd}'.format(cmd=cmd)
    execute(template)


def filr(cmd='get', file='.envs', use_sudo=False):
    if cmd == 'get':
        get(posixpath.join(env.project_dir, file), file)
    elif cmd == 'put':
        put(file, posixpath.join(env.project_dir, file), use_sudo=use_sudo)
        run('chmod go+r {0}'.format(posixpath.join(env.project_dir, file)))


def upload_app():
    rsync_project(
        env.project_dir, './', delete=True)

def upload_www():
    rsync_project('/srv/htdocs/%s/' % env.project_name, './www/', exclude=('node_modules',))

def upload_config():
    virtual_hosts = env.virtual_host.split(',')
    for virtual_host in virtual_hosts:
        put('./etc/nginx-vhost.conf', '/srv/config/%s' % virtual_host)
        run("sed -i 's/{{project_name}}/%s/g' '/srv/config/%s'" % (env.project_name, virtual_host))

def deploy():
    upload_app()


# DANGER!!!
def clean_unused_volumes():
    with settings(warn_only=True):
        run('docker rm -v  $(docker ps --no-trunc -aq status=exited)')
        run('docker rmi $(docker images -q -f "dangling=true")')

    run('docker run --rm'
        '-v /var/run/docker.sock:/var/run/docker.sock '
        '-v /var/lib/docker:/var/lib/docker '
        'martin/docker-cleanup-volumes')


dependency_versions = {
    'git': '2.7.1',
    'python': '3.5.1',
    'conda': '3.14.1',
    'pip': '8.0.2',
    'rsync': '2.6.9',
    'wget': '1.17.1',
    'curl': '7.43.0',
    'grep': '2.5.1',
    'ssh': '1',
    'docker': '1.10.1',
    'docker-compose': '1.6.0',
    'docker-machine': '0.6.0',
    'fab': '1.10.2',
    'brew': '0.9.5',
}


def doctor():
    checkup(check_virtual_env,
            description='Python virtualenv checkup...',
            success='Everything is looking good',
            error='Project environment does not exist. To fix, run\n > conda env create -f etc/environment.yml', )

    check_default_machine()
    check_env_vars()

    checkup(check_depencies,
            description='Checking dependencies...',
            success='All dependencies installed',
            error='Please install missing dependencies', )


def checkup(check_function, description='Checking...',
            success='No problem', error='Errors found'):
    if env.log_level <= logging.DEBUG:
        print(description)

    result = check_function()

    if result['success']:
        if env.log_level <= logging.INFO:
            print(green(success))
    else:
        if env.log_level <= logging.WARNING:
            print(red(error, bold=True))


def check_depencies():
    success = True

    dependencies = [
        'git', 'python', 'conda', 'pip', 'rsync', 'wget', 'curl', 'grep', 'ssh',
        'docker', 'docker-compose', 'docker-machine', 'fab', 'node', 'bower'
    ]

    if os.name == 'nt':
        dependencies += ['choco', ]
    elif sys.platform == 'darwin':
        dependencies += ['brew', ]

    unmet = 0

    for dependency in dependencies:
        path = find_executable(dependency)
        version = ['', ]
        if path:
            if dependency not in ['ssh', ]:
                version_raw = get_result(path + ' --version')
                try:
                    version = re.findall(r'\d+\.\d+\.\d?', version_raw.stderr if version_raw.stderr else version_raw)
                except:
                    pass
            if not version:
                version = ['', ]

            if env.log_level <= logging.DEBUG:
                print('{0} {1:15} {2:20} {3}'.format(
                    green(' O', bold=True), dependency, yellow(version[0], bold=True), os.path.abspath(path)))
        else:
            if env.log_level <= logging.WARNING:
                print(red(' X', bold=True), ' ', dependency)

            unmet += 1

    if unmet > 0:
        success = False

    return {'success': success,}


def check_virtual_env():
    success = True

    conda_envs = get_result('conda info --envs')
    conda_envs = conda_envs.split('\n')[2:]

    for cenv in conda_envs:
        project_env_line = cenv.find(env.virtual_env) != -1

        if cenv.find('*') and project_env_line:
            if env.log_level <= logging.INFO:
                print(green('Project environment found and active:'))
                print(white(cenv))
        elif project_env_line:
            if env.log_level <= logging.WARNING:
                print(yellow('Project environment found, but not activated'))
                print(white('To fix, run:\n > activate tpam'))
            success = False

    return {'success': success, }


def check_default_machine():
    pass


def check_env_vars():
    if env.log_level <= logging.INFO:
        print(white('\nEnvironment checkup', bold=True))

    envs = ['HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'no_proxy', 'conda_default_env']
    for e in envs:
        value = os.environ.get(e, '')
        if value:
            if env.log_level <= logging.INFO:
                print('{0} {1:15} = {2:20}'.format(
                    yellow(' >', bold=True), e, yellow(value, bold=True)))
        else:
            if env.log_level <= logging.INFO:
                print('{0} {1:15}'.format(
                    yellow(' >', bold=True), e))

    if env.log_level <= logging.INFO:
        print(green('Everything is looking good!'))

    if env.log_level <= logging.INFO:
        print(white('\nChecking for .env files', bold=True))

    mandatory_envs = ['SITE_ID', 'DEBUG']
    if os.path.exists('./.local.env'):
        if env.log_level <= logging.INFO:
            print(green('Found .local.env file'))
        os.environ.get('PATH', '')
    else:
        if env.log_level <= logging.ERROR:
            print(red('.local.env does not exist!'))

    if os.path.exists('./.staging.env'):
        if env.log_level <= logging.INFO:
            print(green('Found .staging.env file'))
        os.environ.get('PATH', '')
    else:
        if env.log_level <= logging.ERROR:
            print(red('.staging.env does not exist!'))

    if os.path.exists('./.production.env'):
        if env.log_level <= logging.INFO:
            print(green('Found .production.env file'))
        os.environ.get('PATH', '')
    else:
        if env.log_level <= logging.ERROR:
            print(red('.production.env does not exist!'))


def push_ssh(keyfile):
    with open(keyfile, "r") as myfile:
        keys = myfile.readlines()
    for key in keys:
        key = key.replace('\n', '')
        run('echo {key} >> ~/.ssh/authorized_keys'.format(key=key))

def chown_everything():
    sudo("chown -R %s:%s /srv/" % ('ubuntu', 'ubuntu'))