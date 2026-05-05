# ══════════════════════════════════════════════════════════════
# controllers/auth_controller.py — Contrôleur d'Authentification
# Gère la connexion, déconnexion, inscription et vérification
# de l'utilisateur connecté via les sessions Flask.
# ══════════════════════════════════════════════════════════════

from flask import Blueprint, request, jsonify, session, render_template
from models.user import User

auth_bp = Blueprint('auth', __name__)

# ── GET /login ────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET'])
def login_page():
    """Affiche la page de connexion."""
    return render_template('login.html')

# ── POST /api/auth/login ──────────────────────────────────────
@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """
    Authentifie un utilisateur avec son nom d'utilisateur et mot de passe.
    Si valide, crée une session avec les informations de l'utilisateur.
    La session contient : user_id, username, full_name, role.
    Retourne une erreur 401 si les identifiants sont incorrects.
    """
    data = request.get_json()
    user = User.authenticate(data.get('username', ''), data.get('password', ''))
    if user:
        # Stockage des informations de l'utilisateur dans la session
        session['user_id']   = user.id
        session['username']  = user.username
        session['full_name'] = user.full_name
        session['role']      = user.role
        return jsonify({'success': True, 'full_name': user.full_name, 'role': user.role})
    return jsonify({'success': False, 'error': 'Identifiants incorrects'}), 401

# ── POST /api/auth/register ───────────────────────────────────
@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """
    Crée un nouveau compte utilisateur.
    Rôles disponibles : 'gerant' (accès complet) ou 'employe' (accès limité).
    Le mot de passe doit avoir au moins 6 caractères.
    """
    data = request.get_json()
    username  = data.get('username', '').strip()
    password  = data.get('password', '').strip()
    full_name = data.get('full_name', '').strip()
    role      = data.get('role', 'employe').strip()

    # Validation du rôle
    if role not in ['gerant', 'employe']:
        role = 'employe'

    # Validation des champs obligatoires
    if not username or not password or not full_name:
        return jsonify({'success': False, 'error': 'Tous les champs sont obligatoires'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Mot de passe trop court (6 caractères min)'}), 400

    # Vérification que le nom d'utilisateur n'existe pas déjà
    if User.username_exists(username):
        return jsonify({'success': False, 'error': "Ce nom d'utilisateur existe déjà"}), 400

    if User.create(username, password, full_name, role):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Erreur lors de la création'}), 500

# ── POST /api/auth/logout ─────────────────────────────────────
@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """Déconnecte l'utilisateur en effaçant sa session."""
    session.clear()
    return jsonify({'success': True})

# ── GET /api/auth/me ──────────────────────────────────────────
@auth_bp.route('/api/auth/me', methods=['GET'])
def me():
    """
    Retourne les informations de l'utilisateur actuellement connecté.
    Utilisé par le frontend pour vérifier l'état de la session
    et adapter l'interface selon le rôle (gérant/employé).
    """
    if 'user_id' not in session:
        return jsonify({'logged_in': False}), 401
    return jsonify({
        'logged_in': True,
        'full_name': session.get('full_name'),
        'username':  session.get('username'),
        'role':      session.get('role', 'employe'),
    })
