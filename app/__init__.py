import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_socketio import SocketIO
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.config import Config
from app.extensions import db, migrate

socketio = SocketIO()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def setup_logging(app, base_dir):
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'translator.log'),
        maxBytes=10485760,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    ))
    file_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.INFO)
    app.logger.info('Translator Open-Source Edition Started')


def create_app(basedir=None):
    if basedir:
        os.environ.setdefault('INTERPRETER_BASE_DIR', basedir)

    app = Flask(__name__)
    app.config.from_object(Config)

    effective_basedir = basedir or os.environ.get('INTERPRETER_BASE_DIR') or os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    setup_logging(app, effective_basedir)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes import register_blueprints
    register_blueprints(app)

    @app.after_request
    def add_cors(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return response

    socketio.init_app(
        app,
        async_mode='threading',
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=5 * 1024 * 1024,
        cors_allowed_origins="*"
    )

    from app.socket_handlers import register_socket_handlers
    register_socket_handlers(socketio, app)

    with app.app_context():
        db.create_all()

    return app
