import os
import signal

from app import create_app, socketio


if __name__ == '__main__':
    basedir = os.environ.get('INTERPRETER_BASE_DIR')
    port_str = os.environ.get('PORT', '5004')
    try:
        port = int(port_str)
    except ValueError:
        port = 5004
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    app = create_app(basedir=basedir)

    def handle_sigterm(signum, frame):
        try:
            socketio.stop()
        except RuntimeError:
            pass
        os._exit(0)

    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, handle_sigterm)

    socketio.run(
        app,
        debug=debug,
        host='127.0.0.1',
        port=port,
        allow_unsafe_werkzeug=True
    )
