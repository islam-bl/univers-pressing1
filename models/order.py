"""
Modèle Order — une commande contient un ou plusieurs articles (order_items).

Architecture OOP :
- BaseModel   → helpers DB communs (héritage)
- OrderItem   → encapsule un article de commande avec ses propres propriétés
- Order       → hérite de BaseModel, gère la commande complète

Règles :
- Le statut global de la commande devient 'ready' uniquement quand TOUS les
  articles sont prêts.
- Le prix total = somme des final_price des items.
- Chaque action (création, mise à prêt, retrait) est attribuée à un utilisateur.
- Le gérant voit ses commandes ET celles de ses employés (via manager_id).
"""
import random
import string
from datetime import datetime
from models.database import get_db, DATABASE_URL
from models.catalog import CATALOG, SERVICE_TYPES, get_price
from models.base_model import BaseModel

PH = '%s' if DATABASE_URL else '?'


# ══════════════════════════════════════════════════════════════════
#  Classe OrderItem — encapsule un article de commande
# ══════════════════════════════════════════════════════════════════

class OrderItem:
    """
    Représente un article dans une commande.
    Encapsule les données brutes d'une ligne order_items avec des propriétés
    calculées et des labels traduits.
    """

    def __init__(self, data: dict):
        # Attributs privés (encapsulation)
        self._id              = data.get('id')
        self._order_id        = data.get('order_id')
        self._article_type    = data.get('article_type', '')
        self._service_type    = data.get('service_type', '')
        self._is_high_value   = bool(data.get('is_high_value', 0))
        self._base_price      = float(data.get('base_price') or 0)
        self._final_price     = float(data.get('final_price') or 0)
        self._price_overridden = bool(data.get('price_overridden', 0))
        self._notes           = data.get('notes', '') or ''
        self._status          = data.get('status', 'received')
        self._marked_ready_by = data.get('marked_ready_by')
        self._marked_ready_at = data.get('marked_ready_at')

        # Labels traduits depuis le catalogue
        art = CATALOG.get(self._article_type, {})
        svc = SERVICE_TYPES.get(self._service_type, {})
        self._article_fr = art.get('fr', self._article_type)
        self._article_ar = art.get('ar', '')
        self._service_fr = svc.get('fr', self._service_type)
        self._service_ar = svc.get('ar', '')

    # ── Propriétés (lecture seule) ────────────────────────────

    @property
    def id(self):
        return self._id

    @property
    def order_id(self):
        return self._order_id

    @property
    def article_type(self):
        return self._article_type

    @property
    def service_type(self):
        return self._service_type

    @property
    def is_high_value(self):
        return self._is_high_value

    @property
    def base_price(self):
        return self._base_price

    @property
    def final_price(self):
        return self._final_price

    @property
    def price_overridden(self):
        return self._price_overridden

    @property
    def notes(self):
        return self._notes

    @property
    def status(self):
        return self._status

    @property
    def article_fr(self):
        return self._article_fr

    @property
    def article_ar(self):
        return self._article_ar

    @property
    def service_fr(self):
        return self._service_fr

    @property
    def service_ar(self):
        return self._service_ar

    @property
    def is_ready(self):
        """Retourne True si l'article est prêt ou complété."""
        return self._status in ('ready', 'completed')

    # ── Conversion en dict (pour compatibilité templates Jinja) ─

    def to_dict(self) -> dict:
        """Retourne une représentation dict pour les templates et le JSON."""
        return {
            'id':               self._id,
            'order_id':         self._order_id,
            'article_type':     self._article_type,
            'service_type':     self._service_type,
            'is_high_value':    int(self._is_high_value),
            'base_price':       self._base_price,
            'final_price':      self._final_price,
            'price_overridden': int(self._price_overridden),
            'notes':            self._notes,
            'status':           self._status,
            'marked_ready_by':  self._marked_ready_by,
            'marked_ready_at':  self._marked_ready_at,
            'article_fr':       self._article_fr,
            'article_ar':       self._article_ar,
            'service_fr':       self._service_fr,
            'service_ar':       self._service_ar,
        }

    def __repr__(self):
        return (f"OrderItem(id={self._id}, article={self._article_fr!r}, "
                f"service={self._service_fr!r}, status={self._status!r}, "
                f"price={self._final_price})")


# ══════════════════════════════════════════════════════════════════
#  Classe Order — hérite de BaseModel
# ══════════════════════════════════════════════════════════════════

class Order(BaseModel):
    """
    Représente une commande de pressing.
    Hérite de BaseModel pour les helpers DB.
    Utilise OrderItem pour encapsuler les articles.
    """

    # ── Helpers de génération ─────────────────────────────────

    @staticmethod
    def generate_order_number():
        return f"UP-{datetime.now().strftime('%Y%m%d')}-{''.join(random.choices(string.digits, k=4))}"

    @staticmethod
    def generate_pickup_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    # ── CREATE ───────────────────────────────────────────────

    @staticmethod
    def create(data, items, photo_filename=None, user_id=None, manager_id=None):
        """
        Crée une commande avec une liste d'articles.
        - data  : dict avec customer_name, customer_phone, deposit_date,
                  expected_pickup_date, authorized_person_name,
                  authorized_person_relation, notes
        - items : list de dicts {article_type, service_type, is_high_value,
                                  final_price, price_overridden, notes}
        """
        if not items:
            raise ValueError("Au moins un article est requis pour une commande.")

        order_number = Order.generate_order_number()
        pickup_code  = Order.generate_pickup_code()

        # Construction des items enrichis via OrderItem
        enriched_items = []
        total_price    = 0.0
        for it in items:
            base  = get_price(it.get('article_type'), it.get('service_type')) or 0.0
            final = float(it.get('final_price') or base or 0)
            total_price += final
            item_data = {
                **it,
                'base_price':      base,
                'final_price':     final,
                'is_high_value':   int(it.get('is_high_value', 0) or 0),
                'price_overridden': int(it.get('price_overridden', 0) or 0),
                'notes':           it.get('notes', '') or '',
                'status':          'received',
            }
            enriched_items.append(item_data)

        first = enriched_items[0]

        conn = get_db()
        try:
            if DATABASE_URL:
                c = conn.cursor()
                c.execute(f'''
                    INSERT INTO orders (order_number, pickup_code, customer_name, customer_phone,
                        article_type, service_type, is_high_value, base_price, final_price,
                        total_price, price_overridden, deposit_date, expected_pickup_date,
                        status, global_status,
                        authorized_person_name, authorized_person_relation, article_photo, notes,
                        created_by, manager_id)
                    VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
                    RETURNING id
                ''', (order_number, pickup_code,
                      data.get('customer_name'), data.get('customer_phone'),
                      first['article_type'], first['service_type'],
                      first['is_high_value'], first['base_price'], first['final_price'],
                      total_price, first['price_overridden'],
                      data.get('deposit_date'), data.get('expected_pickup_date'),
                      'received', 'received',
                      data.get('authorized_person_name', ''),
                      data.get('authorized_person_relation', ''),
                      photo_filename, data.get('notes', ''),
                      user_id, manager_id))
                oid = c.fetchone()['id']
                for it in enriched_items:
                    c.execute(f'''
                        INSERT INTO order_items (order_id, article_type, service_type,
                            is_high_value, base_price, final_price, price_overridden, notes, status)
                        VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
                    ''', (oid, it['article_type'], it['service_type'],
                          it['is_high_value'], it['base_price'], it['final_price'],
                          it['price_overridden'], it['notes'], 'received'))
                c.execute(f'INSERT INTO order_history (order_id, action, details, user_id) VALUES ({PH},{PH},{PH},{PH})',
                          (oid, 'created', f"Commande créée pour {data.get('customer_name')} ({len(items)} article(s))", user_id))
                c.execute(f'INSERT INTO operations (order_id, user_id, manager_id, action_type, amount, details) VALUES ({PH},{PH},{PH},{PH},{PH},{PH})',
                          (oid, user_id, manager_id, 'order_created', 0, f"{len(items)} article(s)"))
                conn.commit()
                c.close()
            else:
                cur = conn.execute(f'''
                    INSERT INTO orders (order_number, pickup_code, customer_name, customer_phone,
                        article_type, service_type, is_high_value, base_price, final_price,
                        total_price, price_overridden, deposit_date, expected_pickup_date,
                        status, global_status,
                        authorized_person_name, authorized_person_relation, article_photo, notes,
                        created_by, manager_id)
                    VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
                ''', (order_number, pickup_code,
                      data.get('customer_name'), data.get('customer_phone'),
                      first['article_type'], first['service_type'],
                      first['is_high_value'], first['base_price'], first['final_price'],
                      total_price, first['price_overridden'],
                      data.get('deposit_date'), data.get('expected_pickup_date'),
                      'received', 'received',
                      data.get('authorized_person_name', ''),
                      data.get('authorized_person_relation', ''),
                      photo_filename, data.get('notes', ''),
                      user_id, manager_id))
                oid = cur.lastrowid
                for it in enriched_items:
                    conn.execute(f'''
                        INSERT INTO order_items (order_id, article_type, service_type,
                            is_high_value, base_price, final_price, price_overridden, notes, status)
                        VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
                    ''', (oid, it['article_type'], it['service_type'],
                          it['is_high_value'], it['base_price'], it['final_price'],
                          it['price_overridden'], it['notes'], 'received'))
                conn.execute(f'INSERT INTO order_history (order_id, action, details, user_id) VALUES ({PH},{PH},{PH},{PH})',
                             (oid, 'created', f"Commande créée pour {data.get('customer_name')} ({len(items)} article(s))", user_id))
                conn.execute(f'INSERT INTO operations (order_id, user_id, manager_id, action_type, amount, details) VALUES ({PH},{PH},{PH},{PH},{PH},{PH})',
                             (oid, user_id, manager_id, 'order_created', 0, f"{len(items)} article(s)"))
                conn.commit()
        finally:
            conn.close()

        return Order.get_by_id(oid)

    # ── GET BY ID ────────────────────────────────────────────

    @staticmethod
    def get_by_id(order_id):
        conn    = get_db()
        order   = Order._fetch_one(conn, f'SELECT * FROM orders WHERE id={PH}', (order_id,))
        if not order:
            conn.close()
            return None
        items   = Order._fetch_all(conn, f'SELECT * FROM order_items WHERE order_id={PH} ORDER BY id ASC', (order_id,))
        history = Order._fetch_all(conn, f'SELECT * FROM order_history WHERE order_id={PH} ORDER BY timestamp DESC', (order_id,))
        conn.close()
        return Order._enrich(order, items, history)

    # ── GET BY PICKUP CODE ───────────────────────────────────

    @staticmethod
    def get_by_pickup_code(code, status='ready'):
        conn  = get_db()
        order = Order._fetch_one(
            conn,
            f'SELECT * FROM orders WHERE pickup_code={PH} AND global_status={PH}',
            (code.upper(), status)
        )
        if not order:
            conn.close()
            return None
        items = Order._fetch_all(conn, f'SELECT * FROM order_items WHERE order_id={PH} ORDER BY id ASC', (order['id'],))
        conn.close()
        return Order._enrich(order, items)

    # ── LIST ─────────────────────────────────────────────────

    @staticmethod
    def list_by_status(status=None, user_id=None, manager_id=None, include_team=False):
        """
        - include_team=True : retourne aussi les commandes des employés (gérant)
        - sinon : commandes du seul user_id
        """
        conn   = get_db()
        where  = []
        params = []
        if include_team and manager_id is not None:
            where.append(f"(manager_id={PH} OR created_by={PH})")
            params.extend([manager_id, manager_id])
        elif user_id is not None:
            where.append(f"created_by={PH}")
            params.append(user_id)
        if status:
            where.append(f"global_status={PH}")
            params.append(status)
        sql = "SELECT * FROM orders"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC"
        orders = Order._fetch_all(conn, sql, tuple(params))
        result = []
        for o in orders:
            items = Order._fetch_all(conn, f'SELECT * FROM order_items WHERE order_id={PH} ORDER BY id ASC', (o['id'],))
            result.append(Order._enrich(o, items))
        conn.close()
        return result

    # ── ITEMS : marquer un article prêt ──────────────────────

    @staticmethod
    def mark_item_ready(order_id, item_id, user_id=None):
        """Marque un item comme prêt. Recalcule le statut global de la commande."""
        conn = get_db()
        try:
            now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = Order._fetch_one(conn,
                f'SELECT id FROM order_items WHERE id={PH} AND order_id={PH}',
                (item_id, order_id))
            if not row:
                return None, False
            Order._exec(conn,
                f'UPDATE order_items SET status={PH}, marked_ready_by={PH}, marked_ready_at={PH} WHERE id={PH}',
                ('ready', user_id, now_iso, item_id))
            # Recalcul statut global via OrderItem.is_ready
            raw_items   = Order._fetch_all(conn, f'SELECT status FROM order_items WHERE order_id={PH}', (order_id,))
            order_items = [OrderItem(it) for it in raw_items]
            all_ready   = order_items and all(oi.is_ready for oi in order_items)
            became_ready = False
            current = Order._fetch_one(conn, f'SELECT global_status FROM orders WHERE id={PH}', (order_id,))
            if all_ready and current and current['global_status'] != 'ready':
                Order._exec(conn,
                    f'UPDATE orders SET global_status={PH}, status={PH}, updated_at=CURRENT_TIMESTAMP WHERE id={PH}',
                    ('ready', 'ready', order_id))
                became_ready = True
                Order._exec(conn,
                    f'INSERT INTO order_history (order_id, action, details, user_id) VALUES ({PH},{PH},{PH},{PH})',
                    (order_id, 'status_change', 'received → ready (tous articles prêts)', user_id))
            Order._exec(conn,
                f'INSERT INTO order_history (order_id, action, details, user_id) VALUES ({PH},{PH},{PH},{PH})',
                (order_id, 'item_ready', f'Article #{item_id} marqué prêt', user_id))
            Order._exec(conn,
                f'INSERT INTO operations (order_id, user_id, action_type, amount, details) VALUES ({PH},{PH},{PH},{PH},{PH})',
                (order_id, user_id, 'item_marked_ready', 0, f'item #{item_id}'))
            conn.commit()
        finally:
            conn.close()
        return Order.get_by_id(order_id), became_ready

    # ── COMPLÉTER LA COMMANDE (RETRAIT) ──────────────────────

    @staticmethod
    def complete(order_id, user_id=None):
        conn = get_db()
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            Order._exec(conn,
                f'UPDATE orders SET global_status={PH}, status={PH}, actual_pickup_date={PH}, updated_at=CURRENT_TIMESTAMP WHERE id={PH}',
                ('completed', 'completed', today, order_id))
            Order._exec(conn,
                f"UPDATE order_items SET status='completed' WHERE order_id={PH}",
                (order_id,))
            Order._exec(conn,
                f'INSERT INTO order_history (order_id, action, details, user_id) VALUES ({PH},{PH},{PH},{PH})',
                (order_id, 'status_change', '→ completed', user_id))
            order  = Order._fetch_one(conn, f'SELECT total_price FROM orders WHERE id={PH}', (order_id,))
            amount = float(order['total_price'] or 0) if order else 0
            Order._exec(conn,
                f'INSERT INTO operations (order_id, user_id, action_type, amount, details) VALUES ({PH},{PH},{PH},{PH},{PH})',
                (order_id, user_id, 'pickup_completed', amount, 'Retrait validé'))
            conn.commit()
        finally:
            conn.close()
        return Order.get_by_id(order_id)

    # ── DELETE ───────────────────────────────────────────────

    @staticmethod
    def delete(order_id):
        conn = get_db()
        try:
            row = Order._fetch_one(conn, f'SELECT id FROM orders WHERE id={PH}', (order_id,))
            if not row:
                return False
            Order._exec(conn, f'DELETE FROM order_items WHERE order_id={PH}', (order_id,))
            Order._exec(conn, f'DELETE FROM order_history WHERE order_id={PH}', (order_id,))
            Order._exec(conn, f'DELETE FROM orders WHERE id={PH}', (order_id,))
            conn.commit()
        finally:
            conn.close()
        return True

    # ── SEARCH ───────────────────────────────────────────────

    @staticmethod
    def search(q, user_id=None, manager_id=None, include_team=False):
        conn = get_db()
        like = f'%{q}%'
        op   = 'ILIKE' if DATABASE_URL else 'LIKE'
        if include_team and manager_id is not None:
            sql    = f'''SELECT * FROM orders WHERE (manager_id={PH} OR created_by={PH}) AND (
                customer_name {op} {PH} OR customer_phone {op} {PH}
                OR order_number {op} {PH} OR pickup_code {op} {PH})
                ORDER BY created_at DESC LIMIT 50'''
            params = (manager_id, manager_id, like, like, like, like)
        elif user_id is not None:
            sql    = f'''SELECT * FROM orders WHERE created_by={PH} AND (
                customer_name {op} {PH} OR customer_phone {op} {PH}
                OR order_number {op} {PH} OR pickup_code {op} {PH})
                ORDER BY created_at DESC LIMIT 50'''
            params = (user_id, like, like, like, like)
        else:
            sql    = f'''SELECT * FROM orders WHERE
                customer_name {op} {PH} OR customer_phone {op} {PH}
                OR order_number {op} {PH} OR pickup_code {op} {PH}
                ORDER BY created_at DESC LIMIT 50'''
            params = (like, like, like, like)
        orders = Order._fetch_all(conn, sql, params)
        result = []
        for o in orders:
            items = Order._fetch_all(conn, f'SELECT * FROM order_items WHERE order_id={PH} ORDER BY id ASC', (o['id'],))
            result.append(Order._enrich(o, items))
        conn.close()
        return result

    # ── ENRICH ───────────────────────────────────────────────

    @staticmethod
    def _enrich(order, items=None, history=None):
        """
        Enrichit un dict order avec les labels traduits et les items encapsulés.
        Les items sont convertis en objets OrderItem, puis en dicts pour
        la compatibilité avec les templates Jinja existants.
        """
        art = CATALOG.get(order.get('article_type'), {})
        svc = SERVICE_TYPES.get(order.get('service_type'), {})
        order['article_fr'] = art.get('fr', order.get('article_type', '') or '')
        order['article_ar'] = art.get('ar', '')
        order['service_fr'] = svc.get('fr', order.get('service_type', '') or '')
        order['service_ar'] = svc.get('ar', '')

        # Encapsulation des items via OrderItem, puis export en dict
        order_items = []
        if items:
            for raw in items:
                oi = OrderItem(raw)
                order_items.append(oi.to_dict())

        # Fallback : commande "legacy" sans lignes order_items
        if not order_items and order.get('article_type'):
            order_items.append({
                'id':               None,
                'article_type':     order.get('article_type'),
                'service_type':     order.get('service_type'),
                'is_high_value':    order.get('is_high_value', 0),
                'base_price':       order.get('base_price', 0),
                'final_price':      order.get('final_price', 0),
                'price_overridden': order.get('price_overridden', 0),
                'notes':            order.get('notes', ''),
                'status':           order.get('status', 'received'),
                'article_fr':       art.get('fr', order.get('article_type', '')),
                'article_ar':       art.get('ar', ''),
                'service_fr':       svc.get('fr', order.get('service_type', '')),
                'service_ar':       svc.get('ar', ''),
            })

        order['items']       = order_items
        order['items_count'] = len(order_items)

        # Recalcul total_price
        if order_items:
            order['total_price'] = round(sum(float(it.get('final_price') or 0) for it in order_items), 2)
        else:
            order['total_price'] = float(order.get('total_price') or order.get('final_price') or 0)

        # global_status fallback
        if not order.get('global_status'):
            order['global_status'] = order.get('status', 'received')

        if history is not None:
            order['history'] = history
        return order
