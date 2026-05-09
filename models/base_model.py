"""
BaseModel — Classe mère partagée par Order et User.

Fournit :
- Les helpers DB encapsulés (_exec, _fetch_one, _fetch_all)
- Le placeholder SQL selon la base (PostgreSQL ou SQLite)
- Une interface commune repr/str pour toutes les entités
"""
from models.database import get_db, DATABASE_URL


class BaseModel:
    """
    Classe de base abstraite pour tous les modèles de l'application.
    Encapsule l'accès à la base de données et les helpers SQL communs.
    """

    # ── Attribut de classe : placeholder SQL ─────────────────
    _PH = '%s' if DATABASE_URL else '?'

    # ── Helpers DB encapsulés ─────────────────────────────────

    @staticmethod
    def _exec(conn, sql, params=()):
        """Exécute une requête et retourne le curseur (INSERT/UPDATE/DELETE)."""
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(sql, params)
            return c
        else:
            return conn.execute(sql, params)

    @staticmethod
    def _fetch_one(conn, sql, params=()):
        """Retourne la première ligne en dict, ou None."""
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(sql, params)
            row = c.fetchone()
            c.close()
            return dict(row) if row else None
        else:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    @staticmethod
    def _fetch_all(conn, sql, params=()):
        """Retourne toutes les lignes en liste de dicts."""
        if DATABASE_URL:
            c = conn.cursor()
            c.execute(sql, params)
            rows = c.fetchall()
            c.close()
        else:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def _get_db(cls):
        """Retourne une connexion à la base (raccourci de classe)."""
        return get_db()

    # ── Représentation commune ────────────────────────────────

    def __repr__(self):
        cls = self.__class__.__name__
        attrs = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items() if not k.startswith('_'))
        return f"{cls}({attrs})"

    def __str__(self):
        return self.__repr__()
