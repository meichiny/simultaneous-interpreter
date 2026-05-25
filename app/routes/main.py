import os
import uuid
import requests

from flask import Blueprint, render_template, request, jsonify
from app.config import basedir, Config
from app.models import TermCategory


WS_TEST_URL = "https://openspeech.bytedance.com/api/v4/ast/v2/translate"
WS_TEST_TIMEOUT = 10


def _test_app_key(app_key):
    headers = {
        "X-Api-Key": app_key,
        "X-Api-Resource-Id": "volc.service_type.10053",
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
    try:
        resp = requests.get(WS_TEST_URL, headers=headers, timeout=WS_TEST_TIMEOUT, allow_redirects=False)
        code = resp.status_code
        if code == 101:
            return True, "密钥有效，服务连接成功"
        elif code in (401, 403):
            return False, "密钥无效（请检查 API Key 是否正确）"
        elif code == 400:
            # 400 通常表示请求格式不对但鉴权已过
            return True, "密钥有效，服务连接成功"
        else:
            return False, f"服务返回异常状态 ({code})"
    except requests.exceptions.ConnectTimeout:
        return False, "连接超时（请检查网络连接）"
    except requests.exceptions.ConnectionError:
        return False, "无法连接到翻译服务（请检查网络连接）"
    except Exception as e:
        return False, f"验证异常: {str(e)[:80]}"


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

    # 连接测试：验证密钥有效性
    valid, test_message = _test_app_key(app_key)

    return jsonify({
        'success': True,
        'valid': valid,
        'connected': valid,
        'message': test_message,
    })
