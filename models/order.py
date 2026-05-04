import random, string
from datetime import datetime
from models.database import get_db, DATABASE_URL
from models.catalog import CATALOG, SERVICE_TYPES, get_price

PH = '%s' if DATABASE_URL else '?'

def row_to_dict(row):
    if row is None:
        return None
    if DATABASE_URL:
        return dict(row)
    return dict(row)

class Order:
    @staticmethod
    def generate_order_number():
        date = datetime.now().strftime('%Y%m%d')
        rand = ''.join(random.choices(string.digits, k=4))
        return f"UP-{date}-{rand}"

    @staticmethod
    def generate_pickup_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    @staticmethod
    def create(data, photo_filename=None, user_id=None):
        order_number = Order.generate_order_number()
        pickup_code  = Order.generate_pickup_code()
        base_price   = get_price(data.get('article_type'), data.get('service_type')) or 0.0
        final_price  = float(data.get('final_price', base_price))
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'''
                INSERT INTO orders (order_number,pickup_code,customer_name,customer_phone,
                    article_type,service_type,is_high_value,base_price,final_price,
                    price_overridden,deposit_date,expected_pickup_date,status,
                    authorized_person_name,authorized_person_relation,article_photo,notes,created_by)
                VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
                RETURNING id
            ''', (order_number, pickup_code,
                  data.get('customer_name'), data.get('customer_phone'),
                  data.get('article_type'), data.get('service_type'),
                  int(data.get('is_high_value', 0)), base_price, final_price,
                  int(data.get('price_overridden', 0)),
                  data.get('deposit_date'), data.get('expected_pickup_date'),
                  'received',
                  data.get('authorized_person_name',''), data.get('authorized_person_relation',''),
                  photo_filename, data.get('notes',''), user_id))
            oid = c.fetchone()['id']
            c.execute(f'INSERT INTO order_history (order_id,action,details) VALUES ({PH},{PH},{PH})',
                     (oid, 'created', f"Commande créée pour {data.get('customer_name')}"))
            conn.commit()
            c.execute(f'SELECT * FROM orders WHERE id={PH}', (oid,))
            order = dict(c.fetchone())
            c.close()
        else:
            conn.execute(f'''
                INSERT INTO orders (order_number,pickup_code,customer_name,customer_phone,
                    article_type,service_type,is_high_value,base_price,final_price,
                    price_overridden,deposit_date,expected_pickup_date,status,
                    authorized_person_name,authorized_person_relation,article_photo,notes,created_by)
                VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
            ''', (order_number, pickup_code,
                  data.get('customer_name'), data.get('customer_phone'),
                  data.get('article_type'), data.get('service_type'),
                  int(data.get('is_high_value', 0)), base_price, final_price,
                  int(data.get('price_overridden', 0)),
                  data.get('deposit_date'), data.get('expected_pickup_date'),
                  'received',
                  data.get('authorized_person_name',''), data.get('authorized_person_relation',''),
                  photo_filename, data.get('notes',''), user_id))
            oid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            conn.execute(f'INSERT INTO order_history (order_id,action,details) VALUES ({PH},{PH},{PH})',
                     (oid, 'created', f"Commande créée pour {data.get('customer_name')}"))
            conn.commit()
            order = dict(conn.execute(f'SELECT * FROM orders WHERE id={PH}',(oid,)).fetchone())
        conn.close()
        return Order._enrich(order)

    @staticmethod
    def get_by_id(order_id):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'SELECT * FROM orders WHERE id={PH}', (order_id,))
            row = c.fetchone()
            c.execute(f'SELECT * FROM order_history WHERE order_id={PH} ORDER BY timestamp DESC', (order_id,))
            history = c.fetchall()
            c.close()
        else:
            row = conn.execute(f'SELECT * FROM orders WHERE id={PH}',(order_id,)).fetchone()
            history = conn.execute(f'SELECT * FROM order_history WHERE order_id={PH} ORDER BY timestamp DESC',(order_id,)).fetchall()
        conn.close()
        if not row:
            return None
        order = Order._enrich(dict(row))
        order['history'] = [dict(h) for h in history]
        return order

    @staticmethod
    def get_by_pickup_code(code, status='ready'):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'SELECT * FROM orders WHERE pickup_code={PH} AND status={PH}', (code.upper(), status))
            row = c.fetchone()
            c.close()
        else:
            row = conn.execute(f'SELECT * FROM orders WHERE pickup_code={PH} AND status={PH}',(code.upper(), status)).fetchone()
        conn.close()
        if not row:
            return None
        return Order._enrich(dict(row))

    @staticmethod
    def list_by_status(status=None):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            if status:
                c.execute(f'SELECT * FROM orders WHERE status={PH} ORDER BY created_at DESC', (status,))
            else:
                c.execute('SELECT * FROM orders ORDER BY created_at DESC')
            rows = c.fetchall()
            c.close()
        else:
            if status:
                rows = conn.execute(f'SELECT * FROM orders WHERE status={PH} ORDER BY created_at DESC',(status,)).fetchall()
            else:
                rows = conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
        conn.close()
        return [Order._enrich(dict(r)) for r in rows]

    @staticmethod
    def update_status(order_id, new_status):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'SELECT * FROM orders WHERE id={PH}', (order_id,))
            row = c.fetchone()
            if not row:
                c.close(); conn.close(); return None
            old_status = row['status']
            if new_status == 'completed':
                c.execute(f'UPDATE orders SET status={PH},actual_pickup_date={PH},updated_at=CURRENT_TIMESTAMP WHERE id={PH}',
                         (new_status, datetime.now().strftime('%Y-%m-%d'), order_id))
            else:
                c.execute(f'UPDATE orders SET status={PH},updated_at=CURRENT_TIMESTAMP WHERE id={PH}',(new_status,order_id))
            c.execute(f'INSERT INTO order_history (order_id,action,details) VALUES ({PH},{PH},{PH})',
                     (order_id,'status_change',f'{old_status} → {new_status}'))
            conn.commit()
            c.execute(f'SELECT * FROM orders WHERE id={PH}', (order_id,))
            order = Order._enrich(dict(c.fetchone()))
            c.close()
        else:
            row = conn.execute(f'SELECT * FROM orders WHERE id={PH}',(order_id,)).fetchone()
            if not row:
                conn.close(); return None
            old_status = row['status']
            if new_status == 'completed':
                conn.execute(f'UPDATE orders SET status={PH},actual_pickup_date={PH},updated_at=CURRENT_TIMESTAMP WHERE id={PH}',
                         (new_status, datetime.now().strftime('%Y-%m-%d'), order_id))
            else:
                conn.execute(f'UPDATE orders SET status={PH},updated_at=CURRENT_TIMESTAMP WHERE id={PH}',(new_status,order_id))
            conn.execute(f'INSERT INTO order_history (order_id,action,details) VALUES ({PH},{PH},{PH})',
                     (order_id,'status_change',f'{old_status} → {new_status}'))
            conn.commit()
            order = Order._enrich(dict(conn.execute(f'SELECT * FROM orders WHERE id={PH}',(order_id,)).fetchone()))
        conn.close()
        return order

    @staticmethod
    def update(order_id, data, photo_filename=None):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'SELECT * FROM orders WHERE id={PH}', (order_id,))
            row = c.fetchone()
            if not row:
                c.close(); conn.close(); return None
            base_price = get_price(data.get('article_type'), data.get('service_type')) or 0.0
            final_price = float(data.get('final_price', base_price))
            new_photo = photo_filename if photo_filename else row['article_photo']
            c.execute(f'''
                UPDATE orders SET
                    customer_name={PH}, customer_phone={PH},
                    article_type={PH}, service_type={PH},
                    is_high_value={PH}, base_price={PH}, final_price={PH},
                    price_overridden={PH}, deposit_date={PH}, expected_pickup_date={PH},
                    authorized_person_name={PH}, authorized_person_relation={PH},
                    article_photo={PH}, notes={PH}, updated_at=CURRENT_TIMESTAMP
                WHERE id={PH}
            ''', (data.get('customer_name'), data.get('customer_phone'),
                data.get('article_type'), data.get('service_type'),
                int(data.get('is_high_value', 0)), base_price, final_price,
                int(data.get('price_overridden', 0)),
                data.get('deposit_date'), data.get('expected_pickup_date'),
                data.get('authorized_person_name', ''), data.get('authorized_person_relation', ''),
                new_photo, data.get('notes', ''), order_id))
            c.execute(f'INSERT INTO order_history (order_id,action,details) VALUES ({PH},{PH},{PH})',
                     (order_id, 'updated', "Commande modifiée"))
            conn.commit()
            c.execute(f'SELECT * FROM orders WHERE id={PH}', (order_id,))
            order = Order._enrich(dict(c.fetchone()))
            c.close()
        else:
            row = conn.execute(f'SELECT * FROM orders WHERE id={PH}', (order_id,)).fetchone()
            if not row:
                conn.close(); return None
            base_price = get_price(data.get('article_type'), data.get('service_type')) or 0.0
            final_price = float(data.get('final_price', base_price))
            new_photo = photo_filename if photo_filename else row['article_photo']
            conn.execute(f'''
                UPDATE orders SET
                    customer_name={PH}, customer_phone={PH},
                    article_type={PH}, service_type={PH},
                    is_high_value={PH}, base_price={PH}, final_price={PH},
                    price_overridden={PH}, deposit_date={PH}, expected_pickup_date={PH},
                    authorized_person_name={PH}, authorized_person_relation={PH},
                    article_photo={PH}, notes={PH}, updated_at=CURRENT_TIMESTAMP
                WHERE id={PH}
            ''', (data.get('customer_name'), data.get('customer_phone'),
                data.get('article_type'), data.get('service_type'),
                int(data.get('is_high_value', 0)), base_price, final_price,
                int(data.get('price_overridden', 0)),
                data.get('deposit_date'), data.get('expected_pickup_date'),
                data.get('authorized_person_name', ''), data.get('authorized_person_relation', ''),
                new_photo, data.get('notes', ''), order_id))
            conn.execute(f'INSERT INTO order_history (order_id,action,details) VALUES ({PH},{PH},{PH})',
                     (order_id, 'updated', "Commande modifiée"))
            conn.commit()
            order = Order._enrich(dict(conn.execute(f'SELECT * FROM orders WHERE id={PH}', (order_id,)).fetchone()))
        conn.close()
        return order

    @staticmethod
    def delete(order_id):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'SELECT id FROM orders WHERE id={PH}', (order_id,))
            if not c.fetchone():
                c.close(); conn.close(); return False
            c.execute(f'DELETE FROM order_history WHERE order_id={PH}', (order_id,))
            c.execute(f'DELETE FROM orders WHERE id={PH}', (order_id,))
            conn.commit()
            c.close()
        else:
            if not conn.execute(f'SELECT id FROM orders WHERE id={PH}', (order_id,)).fetchone():
                conn.close(); return False
            conn.execute(f'DELETE FROM order_history WHERE order_id={PH}', (order_id,))
            conn.execute(f'DELETE FROM orders WHERE id={PH}', (order_id,))
            conn.commit()
        conn.close()
        return True

    @staticmethod
    def search(q):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'''SELECT * FROM orders WHERE
                customer_name ILIKE {PH} OR customer_phone ILIKE {PH} OR order_number ILIKE {PH} OR pickup_code ILIKE {PH}
                ORDER BY created_at DESC LIMIT 50''',
                (f'%{q}%',f'%{q}%',f'%{q}%',f'%{q}%'))
            rows = c.fetchall()
            c.close()
        else:
            rows = conn.execute(f'''SELECT * FROM orders WHERE
                customer_name LIKE {PH} OR customer_phone LIKE {PH} OR order_number LIKE {PH} OR pickup_code LIKE {PH}
                ORDER BY created_at DESC LIMIT 50''',
                (f'%{q}%',f'%{q}%',f'%{q}%',f'%{q}%')).fetchall()
        conn.close()
        return [Order._enrich(dict(r)) for r in rows]

    @staticmethod
    def _enrich(order):
        art = CATALOG.get(order.get('article_type'), {})
        svc = SERVICE_TYPES.get(order.get('service_type'), {})
        order['article_fr'] = art.get('fr', order.get('article_type',''))
        order['article_ar'] = art.get('ar', '')
        order['service_fr'] = svc.get('fr', order.get('service_type',''))
        order['service_ar'] = svc.get('ar', '')
        return order
