from flask import Blueprint, request, jsonify
from models.database import get_db, DATABASE_URL
PH = '%s' if DATABASE_URL else '?'

sms_bp = Blueprint('sms', __name__)

def build_whatsapp_message_depot(order):
    """
    Message envoyé au moment du dépôt (création de commande).
    Confirme la prise en charge et informe le client de la date de retrait prévue.
    """
    def fmt_date(d):
        if d and len(d) >= 10:
            parts = d.split('-')
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}"
        return d or ''

    deposit_fmt = fmt_date(order.get('deposit_date'))
    pickup_fmt  = fmt_date(order.get('expected_pickup_date'))

    return (
        f"Bonjour {order.get('customer_name')},\n"
        f"Votre article a bien été déposé chez UNIVERS PRESSING 👕\n"
        f"Commande : {order.get('order_number')}\n"
        f"Dépôt : {deposit_fmt} — Retrait prévu : {pickup_fmt}\n"
        f"Code de retrait : {order.get('pickup_code')}\n"
        f"Nous vous contacterons dès que votre article sera prêt. Merci ! 🙏"
    )


def build_whatsapp_message_ready(order):
    """
    Message envoyé quand la commande est marquée 'Prêt à collecter'.
    Invite le client à venir récupérer son article.
    """
    return (
        f"Bonjour {order.get('customer_name')},\n"
        f"Bonne nouvelle ! Votre article est prêt à être récupéré chez UNIVERS PRESSING ✅\n"
        f"Commande : {order.get('order_number')}\n"
        f"Code de retrait : {order.get('pickup_code')}\n"
        f"Nous sommes disponibles du lundi au samedi. À très bientôt ! 😊"
    )


def build_whatsapp_message(order):
    """
    Compatibilité : utilisé uniquement pour le dépôt (appel depuis api_create).
    """
    return build_whatsapp_message_depot(order)


def build_monthly_reminder(order):
    """Message de rappel mensuel pour article non récupéré."""
    def fmt_date(d):
        if d and len(d) >= 10:
            parts = d.split('-')
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return d or ''
    return (
        f"Bonjour {order.get('customer_name')},\n"
        f"Votre article ({order.get('article_fr')}) déposé le {fmt_date(order.get('deposit_date'))} "
        f"chez UNIVERS PRESSING n'a pas encore été récupéré.\n"
        f"Code de retrait : {order.get('pickup_code')}\n"
        f"Merci de nous contacter au 06 62 77 80 92."
    )


def build_three_month_alert(order, deadline_str):
    """Message d'alerte déclinaison de responsabilité à 3 mois."""
    return (
        f"Bonjour {order.get('customer_name')},\n"
        f"Nous vous informons que si votre article n'est pas récupéré avant le {deadline_str}, "
        f"UNIVERS PRESSING décline toute responsabilité.\n"
        f"Code de retrait : {order.get('pickup_code')}\n"
        f"Contact : 06 62 77 80 92"
    )

def get_twilio_config():
    conn = get_db()
    rows = conn.cursor().execute("SELECT key,value FROM settings WHERE key IN ('twilio_sid','twilio_token','twilio_from')") if DATABASE_URL else None
    conn.close()
    return {r['key']: r['value'] for r in rows}

def send_sms(phone, message):
    cfg = get_twilio_config()
    sid   = cfg.get('twilio_sid','').strip()
    token = cfg.get('twilio_token','').strip()
    from_ = cfg.get('twilio_from','').strip()
    if not sid or not token or not from_:
        return {'sent': False, 'error': 'Twilio non configuré'}
    try:
        from twilio.rest import Client
        client = Client(sid, token)
        msg = client.messages.create(body=message, from_=from_, to=phone)
        return {'sent': True, 'sid': msg.sid}
    except ImportError:
        return {'sent': False, 'error': 'pip install twilio'}
    except Exception as e:
        return {'sent': False, 'error': str(e)}

@sms_bp.route('/api/reminders/monthly', methods=['GET'])
def get_monthly_reminders():
    """Retourne les commandes non récupérées depuis plus d'un mois."""
    from datetime import datetime, timedelta
    from models.order import Order
    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    orders = Order.list_by_status('received') + Order.list_by_status('ready')
    pending = [o for o in orders if o.get('expected_pickup_date','') <= cutoff]
    result = []
    for o in pending:
        msg = build_monthly_reminder(o)
        phone = o.get('customer_phone','').replace(' ','')
        wa_phone = ('212' + phone[1:]) if phone.startswith('0') else phone
        result.append({
            'id': o['id'],
            'customer_name': o['customer_name'],
            'customer_phone': o['customer_phone'],
            'order_number': o['order_number'],
            'pickup_code': o['pickup_code'],
            'article_fr': o.get('article_fr',''),
            'deposit_date': o.get('deposit_date',''),
            'expected_pickup_date': o.get('expected_pickup_date',''),
            'message': msg,
            'wa_link': f"https://wa.me/{wa_phone}?text={__import__('urllib.parse', fromlist=['quote']).parse.quote(msg)}"
        })
    return jsonify(result)


@sms_bp.route('/api/reminders/threemonths', methods=['GET'])
def get_three_month_alerts():
    """Retourne les commandes approchant ou dépassant 3 mois sans retrait."""
    from datetime import datetime, timedelta
    from models.order import Order
    import urllib.parse
    cutoff = (datetime.now() - timedelta(days=80)).strftime('%Y-%m-%d')  # ~2.5 mois → alerte préventive
    orders = Order.list_by_status('received') + Order.list_by_status('ready')
    at_risk = [o for o in orders if o.get('deposit_date','') <= cutoff]
    result = []
    for o in at_risk:
        dep = o.get('deposit_date','')
        try:
            dep_dt = datetime.strptime(dep, '%Y-%m-%d')
            deadline_dt = dep_dt + timedelta(days=90)
            deadline_str = deadline_dt.strftime('%d/%m/%Y')
        except Exception:
            deadline_str = 'bientôt'
        msg = build_three_month_alert(o, deadline_str)
        phone = o.get('customer_phone','').replace(' ','')
        wa_phone = ('212' + phone[1:]) if phone.startswith('0') else phone
        result.append({
            'id': o['id'],
            'customer_name': o['customer_name'],
            'customer_phone': o['customer_phone'],
            'order_number': o['order_number'],
            'pickup_code': o['pickup_code'],
            'article_fr': o.get('article_fr',''),
            'deposit_date': dep,
            'deadline': deadline_str,
            'message': msg,
            'wa_link': f"https://wa.me/{wa_phone}?text={urllib.parse.quote(msg)}"
        })
    return jsonify(result)
