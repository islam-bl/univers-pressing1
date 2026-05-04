import hashlib
from models.database import get_db, DATABASE_URL

ROLES = ['gerant', 'employe']
PH = '%s' if DATABASE_URL else '?'

class User:
    def __init__(self, id, username, full_name, role):
        self.id = id
        self.username = username
        self.full_name = full_name
        self.role = role

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def create(username, password, full_name, role='gerant'):
        if role not in ROLES:
            role = 'employe'
        conn = get_db()
        try:
            if DATABASE_URL:
                c = conn.cursor()
                c.execute(f'INSERT INTO users (username, password_hash, full_name, role) VALUES ({PH},{PH},{PH},{PH})',
                    (username, User.hash_password(password), full_name, role))
                conn.commit()
                c.close()
            else:
                conn.execute(f'INSERT INTO users (username, password_hash, full_name, role) VALUES ({PH},{PH},{PH},{PH})',
                    (username, User.hash_password(password), full_name, role))
                conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def authenticate(username, password):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'SELECT * FROM users WHERE username={PH} AND password_hash={PH}',
                (username, User.hash_password(password)))
            row = c.fetchone()
            c.close()
        else:
            row = conn.execute(f'SELECT * FROM users WHERE username={PH} AND password_hash={PH}',
                (username, User.hash_password(password))).fetchone()
        conn.close()
        if row:
            return User(row['id'], row['username'], row['full_name'], row['role'])
        return None

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'SELECT * FROM users WHERE id={PH}', (user_id,))
            row = c.fetchone()
            c.close()
        else:
            row = conn.execute(f'SELECT * FROM users WHERE id={PH}', (user_id,)).fetchone()
        conn.close()
        if row:
            return User(row['id'], row['username'], row['full_name'], row['role'])
        return None

    @staticmethod
    def username_exists(username):
        conn = get_db()
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(f'SELECT id FROM users WHERE username={PH}', (username,))
            row = c.fetchone()
            c.close()
        else:
            row = conn.execute(f'SELECT id FROM users WHERE username={PH}', (username,)).fetchone()
        conn.close()
        return row is not None
