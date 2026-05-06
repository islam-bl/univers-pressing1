"""
Contrôleur des commandes (multi-articles) + employés.
- Une commande contient un ou plusieurs articles.
- Chaque article peut être marqué prêt indépendamment.
- Le message WhatsApp "prêt" n'est envoyé QU'une seule fois,
  quand TOUS les articles sont prêts.
- Le gérant voit toutes ses commandes + celles de ses employés.
"""
import os
import json
import uuid
from flask import Blueprint, request, jsonify, session
from models.order import Order
from models.user import User
from models.catalog import get_catalog_for_js
from controllers.sms_controller import build_whatsapp_message_depot, build_whatsapp_message_ready

orders_bp = Blueprint('orders', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')


def login_required():
    if 'user_id' not in session:
        return jsonify({'error': 'Non authentifié'}), 401
    return None


def gerant_required():
    err = login_required()
    if err:
        return err
    if session.get('role') != 'gerant':
        return jsonify({'error': 'Accès réservé au gérant'}), 403
    return None


def _current_manager_id():
    """ID du gérant rattaché à l'utilisateur courant.
    - Si gérant : son propre id.
    - Si employé : son manager_id (ou son id si non rattaché — fallback).
    """
    if session.get('role') == 'gerant':
        return session.get('user_id')
    user = User.get_by_id(session.get('user_id'))
    if user and user.manager_id:
        return user.manager_id
    return session.get('user_id')


def _scope_args():
    """Paramètres pour Order.list/search selon le rôle."""
    role = session.get('role')
    uid = session.get('user_id')
    if role == 'gerant':
        return {'manager_id': uid, 'include_team': True}
    return {'user_id': uid}


# ── GET /api/catalog ──────────────────────────────────────────
@orders_bp.route('/api/catalog')
def api_catalog():
    return jsonify(get_catalog_for_js())


# ── GET /api/orders ───────────────────────────────────────────
@orders_bp.route('/api/orders', methods=['GET'])
def api_list():
    err = login_required()
    if err:
        return err
    status = request.args.get('status', '') or None
    orders = Order.list_by_status(status, **_scope_args())
    return jsonify(orders)


# ── POST /api/orders ──────────────────────────────────────────
@orders_bp.route('/api/orders', methods=['POST'])
def api_create():
    """
    Crée une commande contenant 1+ articles.
    Le payload accepte :
      - multipart/form-data avec un champ 'items' = JSON [{...}, ...]
      - OU les anciens champs (article_type, service_type, ...) — fallback.
    """
    err = login_required()
    if err:
        return err

    # Photo (article principal)
    photo_filename = None
    file = request.files.get('article_photo')
    if file and file.filename:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        ext = os.path.splitext(file.filename)[1].lower()
        photo_filename = f"{uuid.uuid4().hex}{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, photo_filename))

    form = request.form

    # Construction de la liste des items
    items = []
    items_raw = form.get('items')
    if items_raw:
        try:
            parsed = json.loads(items_raw)
            if isinstance(parsed, list):
                items = parsed
        except Exception:
            items = []

    if not items:
        # Compatibilité ascendante : un seul article via les champs classiques
        if form.get('article_type') and form.get('service_type'):
            items.append({
                'article_type':     form.get('article_type'),
                'service_type':     form.get('service_type'),
                'is_high_value':    int(form.get('is_high_value', 0) or 0),
                'final_price':      form.get('final_price'),
                'price_overridden': int(form.get('price_overridden', 0) or 0),
                'notes':            form.get('notes', ''),
            })

    if not items:
        return jsonify({'error': 'Aucun article fourni'}), 400

    data = {
        'customer_name':              form.get('customer_name'),
        'customer_phone':             form.get('customer_phone'),
        'deposit_date':               form.get('deposit_date'),
        'expected_pickup_date':       form.get('expected_pickup_date'),
        'authorized_person_name':     form.get('authorized_person_name', ''),
        'authorized_person_relation': form.get('authorized_person_relation', ''),
        'notes':                      form.get('notes', ''),
    }

    user_id = session.get('user_id')
    manager_id = _current_manager_id()
    order = Order.create(data, items, photo_filename, user_id=user_id, manager_id=manager_id)
    msg = build_whatsapp_message_depot(order)
    return jsonify({'success': True, 'order': order, 'whatsapp_msg': msg})


# ── GET /api/orders/<id> ──────────────────────────────────────
@orders_bp.route('/api/orders/<int:oid>', methods=['GET'])
def api_get(oid):
    err = login_required()
    if err:
        return err
    order = Order.get_by_id(oid)
    if not order:
        return jsonify({'error': 'Introuvable'}), 404
    return jsonify(order)


# ── DELETE /api/orders/<id> ───────────────────────────────────
@orders_bp.route('/api/orders/<int:oid>', methods=['DELETE'])
def api_delete(oid):
    err = login_required()
    if err:
        return err
    if not Order.delete(oid):
        return jsonify({'error': 'Introuvable'}), 404
    return jsonify({'success': True})


# ── PUT /api/orders/<id>/items/<item_id>/ready ────────────────
@orders_bp.route('/api/orders/<int:oid>/items/<int:iid>/ready', methods=['PUT'])
def api_item_ready(oid, iid):
    """Marque un article (item) comme prêt. Le statut global passe à 'ready'
    seulement si tous les articles sont prêts."""
    err = login_required()
    if err:
        return err
    order, became_ready = Order.mark_item_ready(oid, iid, user_id=session.get('user_id'))
    if not order:
        return jsonify({'error': 'Article introuvable'}), 404
    result = {'success': True, 'order': order, 'all_ready': became_ready}
    if became_ready:
        result['whatsapp_msg'] = build_whatsapp_message_ready(order)
    return jsonify(result)


# ── PUT /api/orders/<id>/status (legacy) ──────────────────────
@orders_bp.route('/api/orders/<int:oid>/status', methods=['PUT'])
def api_status(oid):
    """Endpoint legacy : passer la commande complète à 'ready' ou 'completed'."""
    err = login_required()
    if err:
        return err
    data = request.get_json() or {}
    new_status = data.get('status')
    if new_status not in ('received', 'ready', 'completed'):
        return jsonify({'error': 'Statut invalide'}), 400

    if new_status == 'completed':
        order = Order.complete(oid, user_id=session.get('user_id'))
    else:
        # Marquer tous les items prêts
        full = Order.get_by_id(oid)
        if not full:
            return jsonify({'error': 'Introuvable'}), 404
        order, became_ready = full, False
        for it in full.get('items', []):
            if it['status'] != 'ready':
                order, became_ready = Order.mark_item_ready(oid, it['id'], user_id=session.get('user_id'))
        if not order:
            order = full
    result = {'success': True, 'order': order}
    if new_status == 'ready' and order.get('global_status') == 'ready':
        result['whatsapp_msg'] = build_whatsapp_message_ready(order)
    return jsonify(result)


# ── GET /api/pickup/<code> ────────────────────────────────────
@orders_bp.route('/api/pickup/<string:code>')
def api_pickup_lookup(code):
    err = login_required()
    if err:
        return err
    order = Order.get_by_pickup_code(code)
    if not order:
        return jsonify({'error': 'Code invalide ou commande non prête'}), 404
    return jsonify(order)


# ── POST /api/pickup/<code>/confirm ───────────────────────────
@orders_bp.route('/api/pickup/<string:code>/confirm', methods=['POST'])
def api_pickup_confirm(code):
    err = login_required()
    if err:
        return err
    order = Order.get_by_pickup_code(code)
    if not order:
        return jsonify({'error': 'Introuvable'}), 404
    Order.complete(order['id'], user_id=session.get('user_id'))
    return jsonify({'success': True})


# ── GET /api/search ───────────────────────────────────────────
@orders_bp.route('/api/search')
def api_search():
    err = login_required()
    if err:
        return err
    q = request.args.get('q', '').strip()
    return jsonify(Order.search(q, **_scope_args()))


# ══════════════════════════════════════════════════════════════
# GESTION DES EMPLOYÉS (réservé au gérant)
# ══════════════════════════════════════════════════════════════

@orders_bp.route('/api/employees', methods=['GET'])
def api_employees_list():
    err = gerant_required()
    if err:
        return err
    return jsonify(User.list_employees(session.get('user_id')))


@orders_bp.route('/api/employees', methods=['POST'])
def api_employees_create():
    err = gerant_required()
    if err:
        return err
    data = request.get_json() or {}
    username = (data.get('username') or '').strip().lower()
    password = (data.get('password') or '').strip()
    full_name = (data.get('full_name') or '').strip()
    if not username or not password or not full_name:
        return jsonify({'success': False, 'error': 'Champs obligatoires manquants'}), 400
    if len(password) < 4:
        return jsonify({'success': False, 'error': 'Mot de passe trop court (4 min)'}), 400
    if User.username_exists(username):
        return jsonify({'success': False, 'error': "Ce nom d'utilisateur existe déjà"}), 400
    ok, err = User.create(username, password, full_name, role='employe', manager_id=session.get('user_id'))
    if not ok:
        return jsonify({'success': False, 'error': err or 'Erreur création employé'}), 500
    return jsonify({'success': True, 'username': username})


@orders_bp.route('/api/employees/<int:uid>', methods=['DELETE'])
def api_employees_delete(uid):
    err = gerant_required()
    if err:
        return err
    if not User.delete_employee(uid, session.get('user_id')):
        return jsonify({'success': False, 'error': 'Introuvable'}), 404
    return jsonify({'success': True})


@orders_bp.route('/api/employees/<int:uid>/password', methods=['PUT'])
def api_employees_password(uid):
    err = gerant_required()
    if err:
        return err
    data = request.get_json() or {}
    pwd = (data.get('password') or '').strip()
    if len(pwd) < 4:
        return jsonify({'success': False, 'error': 'Mot de passe trop court'}), 400
    if not User.update_password(uid, pwd, manager_id=session.get('user_id')):
        return jsonify({'success': False, 'error': 'Introuvable'}), 404
    return jsonify({'success': True})


# ── GET /api/operations : journal d'activité (gérant) ─────────
@orders_bp.route('/api/operations', methods=['GET'])
def api_operations():
    err = gerant_required()
    if err:
        return err
    from models.database import get_db, DATABASE_URL
    PH = '%s' if DATABASE_URL else '?'
    conn = get_db()
    sql = f'''
        SELECT op.*, u.full_name as user_name, o.order_number, o.customer_name
        FROM operations op
        LEFT JOIN users u ON u.id = op.user_id
        LEFT JOIN orders o ON o.id = op.order_id
        WHERE op.manager_id={PH} OR op.user_id={PH}
        ORDER BY op.created_at DESC LIMIT 200
    '''
    if DATABASE_URL:
        c = conn.cursor()
        c.execute(sql, (session.get('user_id'), session.get('user_id')))
        rows = c.fetchall(); c.close()
    else:
        rows = conn.execute(sql, (session.get('user_id'), session.get('user_id'))).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
