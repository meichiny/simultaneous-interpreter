import os

from flask import Blueprint, render_template, request, jsonify
from app.config import basedir
from app.models import TermCategory

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    categories = TermCategory.query.order_by(TermCategory.display_order).all()
    return render_template('index.html', categories=categories)


@main_bp.route('/glossary')
def glossary_management():
    return render_template('glossary.html')


@main_bp.route('/display')
def display_window():
    return render_template('display.html')


@main_bp.route('/api/save_env', methods=['POST'])
def save_env():
    data = request.get_json()
    app_key = data.get('app_key')
    access_key = data.get('access_key')
    if not app_key or not access_key:
        return jsonify({'error': '参数不完整'}), 400

    env_path = os.path.join(basedir, '.env')
    with open(env_path, 'w') as f:
        f.write(f"VOLCANO_APP_KEY={app_key}\n")
        f.write(f"VOLCANO_ACCESS_KEY={access_key}\n")
        f.write(f"FLASK_SECRET_KEY={os.urandom(24).hex()}\n")

    os.environ['VOLCANO_APP_KEY'] = app_key
    os.environ['VOLCANO_ACCESS_KEY'] = access_key

    return jsonify({'success': True})
