# ══════════════════════════════════════════════════════════════
# controllers/order_controller.py — Contrôleur des Commandes
# Définit toutes les routes API REST pour la gestion des commandes.
# Chaque route vérifie que l'utilisateur est connecté (login_required).
# L'isolation des données est assurée par session['user_id'].
# ══════════════════════════════════════════════════════════════

import os, uuid
from flask import Blueprint, request, jsonify, session
from models.order import Order
from models.catalog import get_catalog_for_js, SERVICE_TYPES
from controllers.sms_controller import build_whatsapp_message_depot, build_whatsapp_message_ready

orders_bp = Blueprint('orders', __name__)

# Dossier de stockage des photos des articles
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')

def login_required():
    """Vérifie que l'utilisateur est connecté. Retourne une erreur 401 sinon."""
    if 'user_id' not in session:
        return jsonify({'error': 'Non authentifié'}), 401
    return None

# ── GET /api/catalog ──────────────────────────────────────────
@orders_bp.route('/api/catalog')
def api_catalog():
    """Retourne le catalogue complet des articles et services avec les prix."""
    return jsonify(get_catalog_for_js())

# ── GET /api/orders ───────────────────────────────────────────
@orders_bp.route('/api/orders', methods=['GET'])
def api_list():
    """
    Liste les commandes de l'utilisateur connecté.
    Paramètre optionnel : ?status=received|ready|completed
    Chaque utilisateur ne voit QUE ses propres commandes.
    """
    err = login_required()
    if err: return err
    status = request.args.get('status', '')
    # Filtre par user_id pour l'isolation des données
    user_id = session.get('user_id')
    orders = Order.list_by_status(status if status else None, user_id=user_id)
    return jsonify(orders)

# ── POST /api/orders ──────────────────────────────────────────
@orders_bp.route('/api/orders', methods=['POST'])
def api_create():
    """
    Crée une nouvelle commande.
    Accepte les données du formulaire (multipart/form-data) incluant la photo.
    Associe automatiquement la commande à l'utilisateur connecté.
    """
    err = login_required()
    if err: return err

    # Gestion de l'upload de la photo de l'article
    photo_filename = None
    file = request.files.get('article_photo')
    if file and file.filename:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        ext = os.path.splitext(file.filename)[1].lower()
        photo_filename = f"{uuid.uuid4().hex}{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, photo_filename))

    # Création de la commande avec l'ID de l'utilisateur connecté
    order = Order.create(request.form, photo_filename, session.get('user_id'))

    # Génération du message WhatsApp de confirmation de dépôt
    msg = build_whatsapp_message_depot(order)
    return jsonify({'success': True, 'order': order, 'whatsapp_msg': msg})

# ── PUT /api/orders/<id> ──────────────────────────────────────
@orders_bp.route('/api/orders/<int:oid>', methods=['PUT'])
def api_update(oid):
    """
    Modifie une commande existante.
    Accepte une nouvelle photo optionnelle.
    """
    err = login_required()
    if err: return err

    photo_filename = None
    file = request.files.get('article_photo')
    if file and file.filename:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        ext = os.path.splitext(file.filename)[1].lower()
        photo_filename = f"{uuid.uuid4().hex}{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, photo_filename))

    order = Order.update(oid, request.form, photo_filename)
    if not order:
        return jsonify({'error': 'Introuvable'}), 404
    return jsonify({'success': True, 'order': order})

# ── DELETE /api/orders/<id> ───────────────────────────────────
@orders_bp.route('/api/orders/<int:oid>', methods=['DELETE'])
def api_delete(oid):
    """
    Supprime définitivement une commande.
    Accessible à tous les utilisateurs connectés (gérant ET employé).
    """
    err = login_required()
    if err: return err
    deleted = Order.delete(oid)
    if not deleted:
        return jsonify({'error': 'Introuvable'}), 404
    return jsonify({'success': True})

# ── GET /api/orders/<id> ──────────────────────────────────────
@orders_bp.route('/api/orders/<int:oid>', methods=['GET'])
def api_get(oid):
    """Retourne les détails complets d'une commande avec son historique."""
    err = login_required()
    if err: return err
    order = Order.get_by_id(oid)
    if not order:
        return jsonify({'error': 'Introuvable'}), 404
    return jsonify(order)

# ── PUT /api/orders/<id>/status ───────────────────────────────
@orders_bp.route('/api/orders/<int:oid>/status', methods=['PUT'])
def api_status(oid):
    """
    Met à jour le statut d'une commande.
    Statuts valides : 'received', 'ready', 'completed'
    Envoie un message WhatsApp si la commande passe à 'ready'.
    """
    err = login_required()
    if err: return err
    data = request.get_json()
    new_status = data.get('status')
    if new_status not in ('received', 'ready', 'completed'):
        return jsonify({'error': 'Statut invalide'}), 400
    order = Order.update_status(oid, new_status)
    if not order:
        return jsonify({'error': 'Introuvable'}), 404
    result = {'success': True, 'order': order}
    # Si l'article est prêt, prépare le message WhatsApp pour le client
    if new_status == 'ready':
        result['whatsapp_msg'] = build_whatsapp_message_ready(order)
    return jsonify(result)

# ── GET /api/pickup/<code> ────────────────────────────────────
@orders_bp.route('/api/pickup/<string:code>')
def api_pickup_lookup(code):
    """
    Recherche une commande prête à être retirée par son code de retrait.
    Retourne une erreur si le code est invalide ou la commande non prête.
    """
    err = login_required()
    if err: return err
    order = Order.get_by_pickup_code(code)
    if not order:
        return jsonify({'error': 'Code invalide ou commande non prête'}), 404
    return jsonify(order)

# ── POST /api/pickup/<code>/confirm ───────────────────────────
@orders_bp.route('/api/pickup/<string:code>/confirm', methods=['POST'])
def api_pickup_confirm(code):
    """
    Confirme le retrait d'un article — passe la commande en 'completed'.
    Enregistre la date réelle de retrait.
    """
    err = login_required()
    if err: return err
    order = Order.get_by_pickup_code(code)
    if not order:
        return jsonify({'error': 'Introuvable'}), 404
    Order.update_status(order['id'], 'completed')
    return jsonify({'success': True})

# ── GET /api/search ───────────────────────────────────────────
@orders_bp.route('/api/search')
def api_search():
    """
    Recherche dans les commandes de l'utilisateur connecté.
    Paramètre : ?q=terme_de_recherche
    Cherche dans : nom client, téléphone, numéro de commande, code retrait.
    """
    err = login_required()
    if err: return err
    q = request.args.get('q', '').strip()
    # Filtre par user_id pour n'afficher que ses propres commandes
    user_id = session.get('user_id')
    return jsonify(Order.search(q, user_id=user_id))
