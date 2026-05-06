"""
Modèle User — gestion des comptes (gérant + employés).

Règles :
- Un gérant peut créer des comptes employés liés à lui via manager_id.
- Un employé hérite du manager_id de son créateur.
- has_role / list_employees facilitent la liaison côté contrôleurs.
"""
import hashlib
from models.database import get_db, DATABASE_URL

ROLES = ['gerant', 'employe']
PH = '%s' if DATABASE_URL else '?'


class User:
    def __init__(self, id, username, full_name, role, manager_id=None):
        self.id = id
        self.username = username
        self.full_name = full_name
        self.role = role
        self.manager_id = manager_id

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    # ── CREATE ───────────────────────────────────────────────
    @staticmethod
    def create(username, password, full_name, role='gerant', manager_id=None):
        if role not in ROLES:
            role = 'employe'
        conn = get_db()
        try:
            sql = (f'INSERT INTO users (username, password_hash, full_name, role, manager_id) '
                   f'VALUES ({PH},{PH},{PH},{PH},{PH})')
            params = (username, User.hash_password(password), full_name, role, manager_id)
            if DATABASE_URL:
                c = conn.cursor()
                c.execute(sql, params)
                conn.commit()
                c.close()
            else:
                conn.execute(sql, params)
                conn.commit()
            return True
        except Exception as e:
            print("User.create error:", e)
            return False
        finally:
            conn.close()

    # ── AUTH ─────────────────────────────────────────────────
    @staticmethod
    def authenticate(username, password):
        conn = get_db()
        sql = f'SELECT * FROM users WHERE username={PH} AND password_hash={PH}'
        params = (username, User.hash_password(password))
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(sql, params)
            row = c.fetchone(); c.close()
        else:
            row = conn.execute(sql, params).fetchone()
        conn.close()
        if row:
            return User(row['id'], row['username'], row['full_name'],
                        row['role'], row['manager_id'] if 'manager_id' in row.keys() else None)
        return None

    # ── GET BY ID ────────────────────────────────────────────
    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        sql = f'SELECT * FROM users WHERE id={PH}'
        if DATABASE_URL:
            c = conn.cursor(); c.execute(sql, (user_id,))
            row = c.fetchone(); c.close()
        else:
            row = conn.execute(sql, (user_id,)).fetchone()
        conn.close()
        if row:
            return User(row['id'], row['username'], row['full_name'],
                        row['role'], row['manager_id'] if 'manager_id' in row.keys() else None)
        return None

    @staticmethod
    def username_exists(username):
        conn = get_db()
        sql = f'SELECT id FROM users WHERE username={PH}'
        if DATABASE_URL:
            c = conn.cursor(); c.execute(sql, (username,))
            row = c.fetchone(); c.close()
        else:
            row = conn.execute(sql, (username,)).fetchone()
        conn.close()
        return row is not None

    # ── LISTE DES EMPLOYÉS D'UN GÉRANT ───────────────────────
    @staticmethod
    def list_employees(manager_id):
        conn = get_db()
        sql = f"SELECT id, username, full_name, role, manager_id, created_at FROM users WHERE manager_id={PH} AND role='employe' ORDER BY created_at DESC"
        if DATABASE_URL:
            c = conn.cursor(); c.execute(sql, (manager_id,))
            rows = c.fetchall(); c.close()
        else:
            rows = conn.execute(sql, (manager_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete_employee(user_id, manager_id):
        """Supprime un employé uniquement si rattaché au gérant donné."""
        conn = get_db()
        sql_check = f"SELECT id FROM users WHERE id={PH} AND manager_id={PH} AND role='employe'"
        sql_del = f"DELETE FROM users WHERE id={PH}"
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(sql_check, (user_id, manager_id))
            if not c.fetchone():
                c.close(); conn.close(); return False
            c.execute(sql_del, (user_id,))
            conn.commit(); c.close()
        else:
            row = conn.execute(sql_check, (user_id, manager_id)).fetchone()
            if not row:
                conn.close(); return False
            conn.execute(sql_del, (user_id,))
            conn.commit()
        conn.close()
        return True

    @staticmethod
    def update_password(user_id, new_password, manager_id=None):
        """Reset du mot de passe d'un employé par son gérant."""
        conn = get_db()
        if manager_id is not None:
            sql_check = f"SELECT id FROM users WHERE id={PH} AND manager_id={PH}"
            params_check = (user_id, manager_id)
        else:
            sql_check = f"SELECT id FROM users WHERE id={PH}"
            params_check = (user_id,)
        sql = f'UPDATE users SET password_hash={PH} WHERE id={PH}'
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(sql_check, params_check)
            if not c.fetchone():
                c.close(); conn.close(); return False
            c.execute(sql, (User.hash_password(new_password), user_id))
            conn.commit(); c.close()
        else:
            if not conn.execute(sql_check, params_check).fetchone():
                conn.close(); return False
            conn.execute(sql, (User.hash_password(new_password), user_id))
            conn.commit()
        conn.close()
        return True
