import os, uuid
from flask import Blueprint, request, jsonify, session
from models.order import Order
from models.catalog import get_catalog_for_js, SERVICE_TYPES
from controllers.sms_controller import build_whatsapp_message_depot, build_whatsapp_message_ready

orders_bp = Blueprint('orders', __name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')

def login_required():
    if 'user_id' not in session:
        return jsonify({'error': 'Non authentifié'}), 401
    return None

@orders_bp.route('/api/catalog')
def api_catalog():
    return jsonify(get_catalog_for_js())

@orders_bp.route('/api/orders', methods=['GET'])
def api_list():
    err = login_required()
    if err: return err
    status = request.args.get('status','')
    orders = Order.list_by_status(status if status else None)
    return jsonify(orders)

@orders_bp.route('/api/orders', methods=['POST'])
def api_create():
    err = login_required()
    if err: return err
    photo_filename = None
    file = request.files.get('article_photo')
    if file and file.filename:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        ext = os.path.splitext(file.filename)[1].lower()
        photo_filename = f"{uuid.uuid4().hex}{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, photo_filename))
    order = Order.create(request.form, photo_filename, session.get('user_id'))
    msg = build_whatsapp_message_depot(order)
    return jsonify({'success': True, 'order': order, 'whatsapp_msg': msg})

@orders_bp.route('/api/orders/<int:oid>', methods=['PUT'])
def api_update(oid):
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
    if not order: return jsonify({'error': 'Introuvable'}), 404
    return jsonify({'success': True, 'order': order})

@orders_bp.route('/api/orders/<int:oid>', methods=['DELETE'])
def api_delete(oid):
    err = login_required()
    if err: return err
    deleted = Order.delete(oid)
    if not deleted: return jsonify({'error': 'Introuvable'}), 404
    return jsonify({'success': True})

@orders_bp.route('/api/orders/<int:oid>', methods=['GET'])
def api_get(oid):
    err = login_required()
    if err: return err
    order = Order.get_by_id(oid)
    if not order: return jsonify({'error': 'Introuvable'}), 404
    return jsonify(order)

@orders_bp.route('/api/orders/<int:oid>/status', methods=['PUT'])
def api_status(oid):
    err = login_required()
    if err: return err
    data = request.get_json()
    new_status = data.get('status')
    if new_status not in ('received','ready','completed'):
        return jsonify({'error': 'Statut invalide'}), 400
    order = Order.update_status(oid, new_status)
    if not order: return jsonify({'error': 'Introuvable'}), 404
    result = {'success': True, 'order': order}
    if new_status == 'ready':
        result['whatsapp_msg'] = build_whatsapp_message_ready(order)
    return jsonify(result)

@orders_bp.route('/api/pickup/<string:code>')
def api_pickup_lookup(code):
    err = login_required()
    if err: return err
    order = Order.get_by_pickup_code(code)
    if not order: return jsonify({'error': 'Code invalide ou commande non prête'}), 404
    return jsonify(order)

@orders_bp.route('/api/pickup/<string:code>/confirm', methods=['POST'])
def api_pickup_confirm(code):
    err = login_required()
    if err: return err
    order = Order.get_by_pickup_code(code)
    if not order: return jsonify({'error': 'Introuvable'}), 404
    Order.update_status(order['id'], 'completed')
    return jsonify({'success': True})

@orders_bp.route('/api/search')
def api_search():
    err = login_required()
    if err: return err
    q = request.args.get('q','').strip()
    return jsonify(Order.search(q))
