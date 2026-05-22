import os
from dotenv import load_dotenv

basedir = os.environ.get('INTERPRETER_BASE_DIR')
if not basedir:
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

env_path = os.path.join(basedir, '.env')
if not os.path.exists(env_path):
    home_env = os.path.join(os.path.expanduser('~'), '.config', 'simultaneous-interpreter', '.env')
    if os.path.exists(home_env):
        env_path = home_env
load_dotenv(env_path)


class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'default-key-for-dev-only'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

    VOLCANO_APP_KEY = os.environ.get("VOLCANO_APP_KEY")
    VOLCANO_ACCESS_KEY = os.environ.get("VOLCANO_ACCESS_KEY")
