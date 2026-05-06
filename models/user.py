"""
Modèle User — gestion des comptes (gérant + employés).

Règles :
- Un gérant peut créer des comptes employés liés à lui via manager_id.
- Un employé hérite du manager_id de son créateur.
- L’authentification relit toujours le compte créé en base pour éviter les
  faux "Identifiants incorrects" après création par un gérant.
"""
import hashlib
from models.database import get_db, DATABASE_URL

try:
    from werkzeug.security import check_password_hash
except Exception:  # pragma: no cover - werkzeug est optionnel selon l’hébergement
    check_password_hash = None

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
    def _normalize_username(username):
        return (username or '').strip().lower()

    @staticmethod
    def _row_get(row, key, index=None, default=None):
        if row is None:
            return default
        try:
            return row[key]
        except Exception:
            pass
        if hasattr(row, 'keys') and key in row.keys():
            return row[key]
        if index is not None:
            try:
                return row[index]
            except Exception:
                return default
        return default

    @staticmethod
    def _from_row(row):
        if not row:
            return None
        return User(
            User._row_get(row, 'id', 0),
            User._row_get(row, 'username', 1),
            User._row_get(row, 'full_name', 2),
            User._row_get(row, 'role', 3) or 'employe',
            User._row_get(row, 'manager_id', 4),
        )

    @staticmethod
    def hash_password(password):
        return hashlib.sha256((password or '').encode()).hexdigest()

    @staticmethod
    def _password_matches(stored_password, plain_password):
        stored_password = stored_password or ''
        plain_password = plain_password or ''
        sha_value = User.hash_password(plain_password)
        if stored_password == sha_value:
            return True
        # Compatibilité avec d’anciens comptes éventuellement stockés en clair.
        if stored_password == plain_password:
            return True
        # Compatibilité si une ancienne version utilisait werkzeug.
        if check_password_hash and stored_password.startswith(('pbkdf2:', 'scrypt:')):
            try:
                return check_password_hash(stored_password, plain_password)
            except Exception:
                return False
        return False

    # ── CREATE ───────────────────────────────────────────────
    @staticmethod
    def create(username, password, full_name, role='gerant', manager_id=None):
        username = User._normalize_username(username)
        full_name = (full_name or '').strip()
        role = role if role in ROLES else 'employe'
        if not username or not password or not full_name:
            return False, "Champs obligatoires manquants"

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
            return True, None
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            print("User.create error:", e)
            return False, str(e)
        finally:
            conn.close()

    # ── AUTH ─────────────────────────────────────────────────
    @staticmethod
    def authenticate(username, password):
        username = User._normalize_username(username)
        if not username or password is None:
            return None
        conn = get_db()
        sql = f'SELECT id, username, full_name, role, manager_id, password_hash FROM users WHERE username={PH}'
        try:
            if DATABASE_URL:
                c = conn.cursor()
                c.execute(sql, (username,))
                row = c.fetchone(); c.close()
            else:
                row = conn.execute(sql, (username,)).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        stored_password = User._row_get(row, 'password_hash', 5, '')
        if User._password_matches(stored_password, password):
            return User._from_row(row)
        return None

    # ── GET BY ID ────────────────────────────────────────────
    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        sql = f'SELECT id, username, full_name, role, manager_id FROM users WHERE id={PH}'
        try:
            if DATABASE_URL:
                c = conn.cursor(); c.execute(sql, (user_id,))
                row = c.fetchone(); c.close()
            else:
                row = conn.execute(sql, (user_id,)).fetchone()
        finally:
            conn.close()
        return User._from_row(row)

    @staticmethod
    def username_exists(username):
        username = User._normalize_username(username)
        conn = get_db()
        sql = f'SELECT id FROM users WHERE username={PH}'
        try:
            if DATABASE_URL:
                c = conn.cursor(); c.execute(sql, (username,))
                row = c.fetchone(); c.close()
            else:
                row = conn.execute(sql, (username,)).fetchone()
        finally:
            conn.close()
        return row is not None

    # ── LISTE DES EMPLOYÉS D'UN GÉRANT ───────────────────────
    @staticmethod
    def list_employees(manager_id):
        conn = get_db()
        sql = f"SELECT id, username, full_name, role, manager_id, created_at FROM users WHERE manager_id={PH} AND role='employe' ORDER BY created_at DESC"
        try:
            if DATABASE_URL:
                c = conn.cursor(); c.execute(sql, (manager_id,))
                rows = c.fetchall(); c.close()
            else:
                rows = conn.execute(sql, (manager_id,)).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete_employee(user_id, manager_id):
        """Supprime un employé uniquement si rattaché au gérant donné."""
        conn = get_db()
        sql_check = f"SELECT id FROM users WHERE id={PH} AND manager_id={PH} AND role='employe'"
        sql_del = f"DELETE FROM users WHERE id={PH}"
        try:
            if DATABASE_URL:
                c = conn.cursor()
                c.execute(sql_check, (user_id, manager_id))
                if not c.fetchone():
                    c.close(); return False
                c.execute(sql_del, (user_id,))
                conn.commit(); c.close()
            else:
                row = conn.execute(sql_check, (user_id, manager_id)).fetchone()
                if not row:
                    return False
                conn.execute(sql_del, (user_id,))
                conn.commit()
        finally:
            conn.close()
        return True

    @staticmethod
    def update_password(user_id, new_password, manager_id=None):
        """Reset du mot de passe d'un employé par son gérant."""
        if not new_password:
            return False
        conn = get_db()
        if manager_id is not None:
            sql_check = f"SELECT id FROM users WHERE id={PH} AND manager_id={PH}"
            params_check = (user_id, manager_id)
        else:
            sql_check = f"SELECT id FROM users WHERE id={PH}"
            params_check = (user_id,)
        sql = f'UPDATE users SET password_hash={PH} WHERE id={PH}'
        try:
            if DATABASE_URL:
                c = conn.cursor()
                c.execute(sql_check, params_check)
                if not c.fetchone():
                    c.close(); return False
                c.execute(sql, (User.hash_password(new_password), user_id))
                conn.commit(); c.close()
            else:
                if not conn.execute(sql_check, params_check).fetchone():
                    return False
                conn.execute(sql, (User.hash_password(new_password), user_id))
                conn.commit()
        finally:
            conn.close()
        return True
