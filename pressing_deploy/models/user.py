import hashlib
from models.database import get_db

ROLES = ['gerant', 'employe']

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
            conn.execute(
                'INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)',
                (username, User.hash_password(password), full_name, role)
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def authenticate(username, password):
        conn = get_db()
        row = conn.execute(
            'SELECT * FROM users WHERE username=? AND password_hash=?',
            (username, User.hash_password(password))
        ).fetchone()
        conn.close()
        if row:
            return User(row['id'], row['username'], row['full_name'], row['role'])
        return None

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        row = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        conn.close()
        if row:
            return User(row['id'], row['username'], row['full_name'], row['role'])
        return None

    @staticmethod
    def username_exists(username):
        conn = get_db()
        row = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        conn.close()
        return row is not None
