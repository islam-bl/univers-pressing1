from flask import Blueprint, request, jsonify, session, render_template
from models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.authenticate(data.get('username',''), data.get('password',''))
    if user:
        session['user_id']   = user.id
        session['username']  = user.username
        session['full_name'] = user.full_name
        session['role']      = user.role
        return jsonify({'success': True, 'full_name': user.full_name, 'role': user.role})
    return jsonify({'success': False, 'error': 'Identifiants incorrects'}), 401

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username  = data.get('username','').strip()
    password  = data.get('password','').strip()
    full_name = data.get('full_name','').strip()
    role      = data.get('role','employe').strip()
    if role not in ['gerant','employe']:
        role = 'employe'
    if not username or not password or not full_name:
        return jsonify({'success': False, 'error': 'Tous les champs sont obligatoires'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Mot de passe trop court (6 caractères min)'}), 400
    if User.username_exists(username):
        return jsonify({'success': False, 'error': "Ce nom d'utilisateur existe déjà"}), 400
    if User.create(username, password, full_name, role):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Erreur lors de la création'}), 500

@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@auth_bp.route('/api/auth/me', methods=['GET'])
def me():
    if 'user_id' not in session:
        return jsonify({'logged_in': False}), 401
    return jsonify({
        'logged_in': True,
        'full_name': session.get('full_name'),
        'username':  session.get('username'),
        'role':      session.get('role', 'employe'),
    })
