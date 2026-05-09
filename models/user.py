"""
Modèle User — gestion des comptes (gérant + employés).

Architecture OOP :
- BaseModel  → helpers DB communs (héritage)
- User       → classe de base, attributs encapsulés via @property
- Gerant     → hérite de User, méthodes propres aux gérants
- Employe    → hérite de User, méthodes propres aux employés

Règles :
- Un gérant peut créer des comptes employés liés à lui via manager_id.
- Un employé hérite du manager_id de son créateur.
- L'authentification relit toujours le compte créé en base pour éviter les
  faux "Identifiants incorrects" après création par un gérant.
"""
import hashlib
from models.database import get_db, DATABASE_URL
from models.base_model import BaseModel

try:
    from werkzeug.security import check_password_hash
except Exception:
    check_password_hash = None

ROLES = ['gerant', 'employe']
PH = '%s' if DATABASE_URL else '?'


# ══════════════════════════════════════════════════════════════════
#  Classe de base : User
# ══════════════════════════════════════════════════════════════════

class User(BaseModel):
    """
    Représente un utilisateur de l'application.
    Les attributs sont encapsulés via @property pour contrôler l'accès.
    """

    def __init__(self, id, username, full_name, role, manager_id=None):
        # Attributs privés (encapsulation)
        self._id = id
        self._username = username
        self._full_name = full_name
        self._role = role if role in ROLES else 'employe'
        self._manager_id = manager_id

    # ── Propriétés (lecture seule) ────────────────────────────

    @property
    def id(self):
        return self._id

    @property
    def username(self):
        return self._username

    @property
    def full_name(self):
        return self._full_name

    @property
    def role(self):
        return self._role

    @property
    def manager_id(self):
        return self._manager_id

    @property
    def is_gerant(self):
        """Retourne True si l'utilisateur est un gérant."""
        return self._role == 'gerant'

    @property
    def is_employe(self):
        """Retourne True si l'utilisateur est un employé."""
        return self._role == 'employe'

    # ── Méthodes utilitaires internes ────────────────────────

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
        """Instancie le bon sous-type (Gerant ou Employe) depuis une ligne DB."""
        if not row:
            return None
        role = User._row_get(row, 'role', 3) or 'employe'
        id_        = User._row_get(row, 'id', 0)
        username   = User._row_get(row, 'username', 1)
        full_name  = User._row_get(row, 'full_name', 2)
        manager_id = User._row_get(row, 'manager_id', 4)

        # Instanciation polymorphique
        if role == 'gerant':
            return Gerant(id_, username, full_name, manager_id)
        return Employe(id_, username, full_name, manager_id)

    # ── Sécurité / mot de passe ───────────────────────────────

    @staticmethod
    def hash_password(password):
        return hashlib.sha256((password or '').encode()).hexdigest()

    @staticmethod
    def _password_matches(stored_password, plain_password):
        stored_password = stored_password or ''
        plain_password  = plain_password or ''
        sha_value = User.hash_password(plain_password)
        if stored_password == sha_value:
            return True
        if stored_password == plain_password:
            return True
        if check_password_hash and stored_password.startswith(('pbkdf2:', 'scrypt:')):
            try:
                return check_password_hash(stored_password, plain_password)
            except Exception:
                return False
        return False

    # ── CREATE ───────────────────────────────────────────────

    @staticmethod
    def create(username, password, full_name, role='gerant', manager_id=None):
        username  = User._normalize_username(username)
        full_name = (full_name or '').strip()
        role      = role if role in ROLES else 'employe'
        if not username or not password or not full_name:
            return False, "Champs obligatoires manquants"

        conn = get_db()
        try:
            sql    = (f'INSERT INTO users (username, password_hash, full_name, role, manager_id) '
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
        sql = (f'SELECT id, username, full_name, role, manager_id, password_hash '
               f'FROM users WHERE username={PH}')
        try:
            if DATABASE_URL:
                c   = conn.cursor()
                c.execute(sql, (username,))
                row = c.fetchone()
                c.close()
            else:
                row = conn.execute(sql, (username,)).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        stored = User._row_get(row, 'password_hash', 5, '')
        if User._password_matches(stored, password):
            return User._from_row(row)
        return None

    # ── GET BY ID ────────────────────────────────────────────

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        sql  = f'SELECT id, username, full_name, role, manager_id FROM users WHERE id={PH}'
        try:
            if DATABASE_URL:
                c   = conn.cursor()
                c.execute(sql, (user_id,))
                row = c.fetchone()
                c.close()
            else:
                row = conn.execute(sql, (user_id,)).fetchone()
        finally:
            conn.close()
        return User._from_row(row)

    @staticmethod
    def username_exists(username):
        username = User._normalize_username(username)
        conn = get_db()
        sql  = f'SELECT id FROM users WHERE username={PH}'
        try:
            if DATABASE_URL:
                c   = conn.cursor()
                c.execute(sql, (username,))
                row = c.fetchone()
                c.close()
            else:
                row = conn.execute(sql, (username,)).fetchone()
        finally:
            conn.close()
        return row is not None

    @staticmethod
    def update_password(user_id, new_password, manager_id=None):
        """Reset du mot de passe — accessible au gérant ou à l'utilisateur lui-même."""
        if not new_password:
            return False
        conn = get_db()
        if manager_id is not None:
            sql_check    = f'SELECT id FROM users WHERE id={PH} AND manager_id={PH}'
            params_check = (user_id, manager_id)
        else:
            sql_check    = f'SELECT id FROM users WHERE id={PH}'
            params_check = (user_id,)
        sql = f'UPDATE users SET password_hash={PH} WHERE id={PH}'
        try:
            if DATABASE_URL:
                c = conn.cursor()
                c.execute(sql_check, params_check)
                if not c.fetchone():
                    c.close()
                    return False
                c.execute(sql, (User.hash_password(new_password), user_id))
                conn.commit()
                c.close()
            else:
                if not conn.execute(sql_check, params_check).fetchone():
                    return False
                conn.execute(sql, (User.hash_password(new_password), user_id))
                conn.commit()
        finally:
            conn.close()
        return True


# ══════════════════════════════════════════════════════════════════
#  Sous-classe : Gerant  (hérite de User)
# ══════════════════════════════════════════════════════════════════

class Gerant(User):
    """
    Gérant du pressing.
    Hérite de User et ajoute les opérations propres à la gestion d'équipe.
    """

    def __init__(self, id, username, full_name, manager_id=None):
        super().__init__(id, username, full_name, 'gerant', manager_id)

    # ── Gestion des employés ──────────────────────────────────

    def list_employees(self):
        """Retourne la liste des employés rattachés à ce gérant."""
        conn = get_db()
        sql  = (f"SELECT id, username, full_name, role, manager_id, created_at "
                f"FROM users WHERE manager_id={PH} AND role='employe' ORDER BY created_at DESC")
        try:
            if DATABASE_URL:
                c    = conn.cursor()
                c.execute(sql, (self._id,))
                rows = c.fetchall()
                c.close()
            else:
                rows = conn.execute(sql, (self._id,)).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def delete_employee(self, user_id):
        """Supprime un employé uniquement si rattaché à ce gérant."""
        conn = get_db()
        sql_check = (f"SELECT id FROM users WHERE id={PH} AND manager_id={PH} AND role='employe'")
        sql_del   = f'DELETE FROM users WHERE id={PH}'
        try:
            if DATABASE_URL:
                c = conn.cursor()
                c.execute(sql_check, (user_id, self._id))
                if not c.fetchone():
                    c.close()
                    return False
                c.execute(sql_del, (user_id,))
                conn.commit()
                c.close()
            else:
                if not conn.execute(sql_check, (user_id, self._id)).fetchone():
                    return False
                conn.execute(sql_del, (user_id,))
                conn.commit()
        finally:
            conn.close()
        return True

    def create_employee(self, username, password, full_name):
        """Crée un compte employé rattaché à ce gérant."""
        return User.create(username, password, full_name, role='employe', manager_id=self._id)

    # ── Compatibilité rétrograde (méthodes statiques conservées) ─

    @staticmethod
    def list_employees_for(manager_id):
        """Version statique pour compatibilité avec l'ancien code."""
        conn = get_db()
        sql  = (f"SELECT id, username, full_name, role, manager_id, created_at "
                f"FROM users WHERE manager_id={PH} AND role='employe' ORDER BY created_at DESC")
        try:
            if DATABASE_URL:
                c    = conn.cursor()
                c.execute(sql, (manager_id,))
                rows = c.fetchall()
                c.close()
            else:
                rows = conn.execute(sql, (manager_id,)).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete_employee_static(user_id, manager_id):
        """Version statique pour compatibilité avec l'ancien code."""
        conn = get_db()
        sql_check = (f"SELECT id FROM users WHERE id={PH} AND manager_id={PH} AND role='employe'")
        sql_del   = f'DELETE FROM users WHERE id={PH}'
        try:
            if DATABASE_URL:
                c = conn.cursor()
                c.execute(sql_check, (user_id, manager_id))
                if not c.fetchone():
                    c.close()
                    return False
                c.execute(sql_del, (user_id,))
                conn.commit()
                c.close()
            else:
                if not conn.execute(sql_check, (user_id, manager_id)).fetchone():
                    return False
                conn.execute(sql_del, (user_id,))
                conn.commit()
        finally:
            conn.close()
        return True


# ══════════════════════════════════════════════════════════════════
#  Sous-classe : Employe  (hérite de User)
# ══════════════════════════════════════════════════════════════════

class Employe(User):
    """
    Employé du pressing.
    Hérite de User. Ses actions sont limitées à ses propres commandes.
    """

    def __init__(self, id, username, full_name, manager_id=None):
        super().__init__(id, username, full_name, 'employe', manager_id)

    @property
    def gerant_id(self):
        """Alias lisible pour manager_id."""
        return self._manager_id

    def can_manage_employees(self):
        """Un employé ne peut pas gérer d'autres comptes."""
        return False


# ══════════════════════════════════════════════════════════════════
#  Rétrocompatibilité : les controllers utilisent User.list_employees
#  et User.delete_employee en tant que méthodes statiques.
# ══════════════════════════════════════════════════════════════════

# On réexpose les méthodes statiques sur User pour ne pas casser
# le code existant dans auth_controller.py.
User.list_employees = staticmethod(Gerant.list_employees_for)
User.delete_employee = staticmethod(Gerant.delete_employee_static)
