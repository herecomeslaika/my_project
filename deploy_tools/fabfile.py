from fabric.api import env, run, cd, sudo, local, put, settings
from fabric.contrib.files import exists
import os
import random
import string

# Server config
env.user = 'yyy'
env.hosts = ['8.149.137.130']
env.password = '525jihaoyangZPU,'

SITENAME = '8.149.137.130'
BASE_DIR = f'/home/yyy/sites/{SITENAME}'
SOURCE_DIR = f'{BASE_DIR}/source'
VENV_DIR = f'{BASE_DIR}/virtualenv'
REPO_URL = 'https://github.com/herecomeslaika/my_project.git'


def _generate_secret_key(length=50):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))


def deploy():
    """Full deployment: create dirs, pull code, configure, install deps, migrate, collectstatic."""
    _create_directory_structure()
    _pull_source()
    _update_settings()
    _update_virtualenv()
    _collectstatic()
    _migrate()
    _restart_gunicorn()


def _create_directory_structure():
    """Create the site directory structure if it doesn't exist."""
    for subdir in ('database', 'static', 'virtualenv', 'source'):
        run(f'mkdir -p {BASE_DIR}/{subdir}')


def _pull_source():
    """Clone or update the source code from GitHub."""
    if exists(f'{SOURCE_DIR}/.git'):
        with cd(SOURCE_DIR):
            run('git fetch')
            run('git reset --hard origin/master')
    else:
        run(f'git clone {REPO_URL} {SOURCE_DIR}')


def _update_settings():
    """Update settings.py for production: DEBUG, ALLOWED_HOSTS, SECRET_KEY, paths."""
    settings_path = f'{SOURCE_DIR}/mywebsite/mywebsite/settings.py'

    # DEBUG = False
    run(f"sed -i 's/DEBUG = True/DEBUG = False/' {settings_path}")

    # ALLOWED_HOSTS
    run(f"sed -i \"s/ALLOWED_HOSTS = .*/ALLOWED_HOSTS = ['{SITENAME}']/\" {settings_path}")

    # Fix paths for server directory structure (../ → ../../)
    run(f"sed -i \"s|os.path.join(BASE_DIR, '../database/db.sqlite3')|os.path.join(BASE_DIR, '../../database/db.sqlite3')|g\" {settings_path}")
    run(f"sed -i \"s|os.path.join(BASE_DIR, '../static/')|os.path.join(BASE_DIR, '../../static/')|g\" {settings_path}")

    # SECRET_KEY: generate if not already set in a separate file
    secret_key_file = f'{BASE_DIR}/.secret_key'
    if not exists(secret_key_file):
        secret_key = _generate_secret_key()
        run(f"echo '{secret_key}' > {secret_key_file}")
    run(f"sed -i \"s/SECRET_KEY = .*/SECRET_KEY = open('{secret_key_file}').read().strip()/\" {settings_path}")


def _update_virtualenv():
    """Create virtualenv if needed and install requirements."""
    if not exists(f'{VENV_DIR}/bin/pip'):
        run(f'python3 -m venv {VENV_DIR}')
    run(f'{VENV_DIR}/bin/pip install -r {SOURCE_DIR}/mywebsite/requirements.txt')


def _collectstatic():
    """Collect static files."""
    with cd(f'{SOURCE_DIR}/mywebsite'):
        run(f'{VENV_DIR}/bin/python manage.py collectstatic --noinput')
    # Ensure Nginx (www-data) can traverse path and read static files
    sudo('chmod o+x /home/yyy /home/yyy/sites')
    sudo(f'chmod o+x {BASE_DIR}')
    sudo(f'chmod -R o+rX {BASE_DIR}/static')


def _migrate():
    """Run database migrations."""
    with cd(f'{SOURCE_DIR}/mywebsite'):
        run(f'{VENV_DIR}/bin/python manage.py migrate --noinput')


def _restart_gunicorn():
    """Restart the Gunicorn systemd service."""
    sudo('systemctl daemon-reload')
    sudo(f'systemctl restart gunicorn-{SITENAME}')


def nginx_config():
    """Deploy Nginx config from template."""
    template_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(template_dir, 'nginx.template.conf')

    with open(template_path) as f:
        config_text = f.read().replace('SITENAME', SITENAME)

    # Write to temp file, then move with sudo
    temp_path = '/tmp/nginx_site_config'
    run(f"cat > {temp_path} << 'EOF'\n{config_text}\nEOF")
    sudo(f'mv {temp_path} /etc/nginx/sites-available/{SITENAME}')
    sudo(f'ln -sf /etc/nginx/sites-available/{SITENAME} /etc/nginx/sites-enabled/')
    sudo('rm -f /etc/nginx/sites-enabled/default')
    sudo('nginx -t')
    sudo('systemctl reload nginx')


def gunicorn_config():
    """Deploy Gunicorn systemd service from template."""
    template_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(template_dir, 'gunicorn-systemd.template.service')

    with open(template_path) as f:
        config_text = f.read().replace('SITENAME', SITENAME)

    temp_path = '/tmp/gunicorn_service_config'
    run(f"cat > {temp_path} << 'EOF'\n{config_text}\nEOF")
    sudo(f'mv {temp_path} /etc/systemd/system/gunicorn-{SITENAME}.service')
    sudo('systemctl daemon-reload')
    sudo(f'systemctl enable gunicorn-{SITENAME}')
    sudo(f'systemctl restart gunicorn-{SITENAME}')
