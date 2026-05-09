import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, send_from_directory, session, redirect, url_for
from models.database import init_db
from controllers.auth_controller import auth_bp
from controllers.order_controller import orders_bp
from controllers.sms_controller import sms_bp

def create_app():
    app = Flask(__name__, template_folder='views/templates', static_folder='static')
    app.secret_key = os.environ.get('SECRET_KEY', 'univers-pressing-secret-key-2024')

    os.makedirs(os.path.join(os.path.dirname(__file__), 'static', 'uploads'), exist_ok=True)

    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(sms_bp)

    @app.route('/')
    def index():
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        return render_template('index.html')

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'static', 'uploads'), filename)

    return app

app = create_app()

# Important : init_db() doit être appelé au chargement du module pour que
# Gunicorn (Railway / Procfile : "web: gunicorn app:app") crée les tables
# manquantes (order_items) et applique les migrations légères (manager_id,
# global_status, total_price, ...).
try:
    init_db()
except Exception as _e:
    print("init_db() au démarrage a échoué :", _e)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*55)
    print("  Univers Pressing — Systeme de Gestion v2")
    print(f"  Ouvrir: http://0.0.0.0:{port}")
    print("="*55 + "\n")
import webbrowser
import threading

if __name__ == '__main__':
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host='0.0.0.0', port=5000)
