import os

from flask import Blueprint, render_template, request, jsonify
from app.config import basedir, Config
from app.models import TermCategory

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    categories = TermCategory.query.order_by(TermCategory.display_order).all()
    return render_template('index.html', categories=categories, has_api_key=bool(Config.VOLCANO_APP_KEY))


@main_bp.route('/glossary')
def glossary_management():
    return render_template('glossary.html')


@main_bp.route('/display')
def display_window():
    return render_template('display.html')


@main_bp.route('/api/save_env', methods=['POST'])
def save_env():
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效的 JSON 请求体'}), 400

    app_key = data.get('app_key')
    if not app_key:
        return jsonify({'error': '参数不完整'}), 400

    if '\n' in app_key:
        return jsonify({'error': '密钥不能包含换行符'}), 400

    env_path = os.path.join(basedir, '.env')
    existing = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    k, v = line.split('=', 1)
                    existing[k] = v
    existing['VOLCANO_APP_KEY'] = app_key
    existing.pop('VOLCANO_ACCESS_KEY', None)
    if 'FLASK_SECRET_KEY' not in existing:
        existing['FLASK_SECRET_KEY'] = os.urandom(24).hex()
    with open(env_path, 'w') as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    os.environ['VOLCANO_APP_KEY'] = app_key
    os.environ.pop('VOLCANO_ACCESS_KEY', None)
    Config.VOLCANO_APP_KEY = app_key

    return jsonify({'success': True})
