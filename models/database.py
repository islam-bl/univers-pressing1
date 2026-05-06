"""
Initialisation et accès à la base de données.
- Supporte SQLite (local) et PostgreSQL (Railway via DATABASE_URL).
- Crée les tables si elles n'existent pas.
- Applique des migrations idempotentes pour les bases déjà en production.
"""
import os
import sqlite3

DATABASE_URL = os.environ.get('DATABASE_URL')


def get_db():
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        url = DATABASE_URL
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)

    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'pressing.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ── Helpers de migration légère ─────────────────────────────────
def _pg_column_exists(c, table, column):
    c.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = ANY (current_schemas(false))
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table, column),
    )
    return c.fetchone() is not None


def _sqlite_column_exists(conn, table, column):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _safe_pg_execute(conn, sql, label):
    c = conn.cursor()
    try:
        c.execute(sql)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"Migration ignorée ({label}) : {exc}")
    finally:
        c.close()


def _safe_sqlite_execute(conn, sql, label):
    try:
        conn.execute(sql)
        conn.commit()
    except Exception as exc:
        print(f"Migration ignorée ({label}) : {exc}")


def _ensure_pg_column(conn, table, column, ddl):
    c = conn.cursor()
    try:
        exists = _pg_column_exists(c, table, column)
    finally:
        c.close()
    if not exists:
        _safe_pg_execute(conn, ddl, f"{table}.{column}")


def _ensure_sqlite_column(conn, table, column, ddl):
    try:
        exists = _sqlite_column_exists(conn, table, column)
    except Exception:
        exists = False
    if not exists:
        _safe_sqlite_execute(conn, ddl, f"{table}.{column}")


def _init_postgres(conn):
    _safe_pg_execute(conn, """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'gerant',
            manager_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, "create users")
    for column, ddl in [
        ('username', "ALTER TABLE users ADD COLUMN username TEXT"),
        ('password_hash', "ALTER TABLE users ADD COLUMN password_hash TEXT"),
        ('full_name', "ALTER TABLE users ADD COLUMN full_name TEXT"),
        ('role', "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'gerant'"),
        ('manager_id', "ALTER TABLE users ADD COLUMN manager_id INTEGER"),
        ('created_at', "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]:
        _ensure_pg_column(conn, 'users', column, ddl)

    _safe_pg_execute(conn, """
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            order_number TEXT UNIQUE NOT NULL,
            pickup_code TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            article_type TEXT,
            service_type TEXT,
            is_high_value INTEGER DEFAULT 0,
            base_price REAL DEFAULT 0,
            final_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0,
            price_overridden INTEGER DEFAULT 0,
            deposit_date TEXT NOT NULL,
            expected_pickup_date TEXT NOT NULL,
            actual_pickup_date TEXT,
            status TEXT NOT NULL DEFAULT 'received',
            global_status TEXT DEFAULT 'received',
            authorized_person_name TEXT,
            authorized_person_relation TEXT,
            article_photo TEXT,
            notes TEXT,
            created_by INTEGER,
            manager_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, "create orders")
    for column, ddl in [
        ('order_number', "ALTER TABLE orders ADD COLUMN order_number TEXT"),
        ('pickup_code', "ALTER TABLE orders ADD COLUMN pickup_code TEXT"),
        ('customer_name', "ALTER TABLE orders ADD COLUMN customer_name TEXT"),
        ('customer_phone', "ALTER TABLE orders ADD COLUMN customer_phone TEXT"),
        ('article_type', "ALTER TABLE orders ADD COLUMN article_type TEXT"),
        ('service_type', "ALTER TABLE orders ADD COLUMN service_type TEXT"),
        ('is_high_value', "ALTER TABLE orders ADD COLUMN is_high_value INTEGER DEFAULT 0"),
        ('base_price', "ALTER TABLE orders ADD COLUMN base_price REAL DEFAULT 0"),
        ('final_price', "ALTER TABLE orders ADD COLUMN final_price REAL DEFAULT 0"),
        ('total_price', "ALTER TABLE orders ADD COLUMN total_price REAL DEFAULT 0"),
        ('price_overridden', "ALTER TABLE orders ADD COLUMN price_overridden INTEGER DEFAULT 0"),
        ('deposit_date', "ALTER TABLE orders ADD COLUMN deposit_date TEXT"),
        ('expected_pickup_date', "ALTER TABLE orders ADD COLUMN expected_pickup_date TEXT"),
        ('actual_pickup_date', "ALTER TABLE orders ADD COLUMN actual_pickup_date TEXT"),
        ('status', "ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'received'"),
        ('global_status', "ALTER TABLE orders ADD COLUMN global_status TEXT DEFAULT 'received'"),
        ('authorized_person_name', "ALTER TABLE orders ADD COLUMN authorized_person_name TEXT"),
        ('authorized_person_relation', "ALTER TABLE orders ADD COLUMN authorized_person_relation TEXT"),
        ('article_photo', "ALTER TABLE orders ADD COLUMN article_photo TEXT"),
        ('notes', "ALTER TABLE orders ADD COLUMN notes TEXT"),
        ('created_by', "ALTER TABLE orders ADD COLUMN created_by INTEGER"),
        ('manager_id', "ALTER TABLE orders ADD COLUMN manager_id INTEGER"),
        ('created_at', "ALTER TABLE orders ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ('updated_at', "ALTER TABLE orders ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]:
        _ensure_pg_column(conn, 'orders', column, ddl)

    _safe_pg_execute(conn, """
        CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            article_type TEXT NOT NULL,
            service_type TEXT NOT NULL,
            is_high_value INTEGER DEFAULT 0,
            base_price REAL DEFAULT 0,
            final_price REAL DEFAULT 0,
            price_overridden INTEGER DEFAULT 0,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'received',
            marked_ready_by INTEGER,
            marked_ready_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, "create order_items")
    for column, ddl in [
        ('order_id', "ALTER TABLE order_items ADD COLUMN order_id INTEGER"),
        ('article_type', "ALTER TABLE order_items ADD COLUMN article_type TEXT"),
        ('service_type', "ALTER TABLE order_items ADD COLUMN service_type TEXT"),
        ('is_high_value', "ALTER TABLE order_items ADD COLUMN is_high_value INTEGER DEFAULT 0"),
        ('base_price', "ALTER TABLE order_items ADD COLUMN base_price REAL DEFAULT 0"),
        ('final_price', "ALTER TABLE order_items ADD COLUMN final_price REAL DEFAULT 0"),
        ('price_overridden', "ALTER TABLE order_items ADD COLUMN price_overridden INTEGER DEFAULT 0"),
        ('notes', "ALTER TABLE order_items ADD COLUMN notes TEXT"),
        ('status', "ALTER TABLE order_items ADD COLUMN status TEXT DEFAULT 'received'"),
        ('marked_ready_by', "ALTER TABLE order_items ADD COLUMN marked_ready_by INTEGER"),
        ('marked_ready_at', "ALTER TABLE order_items ADD COLUMN marked_ready_at TIMESTAMP"),
        ('created_at', "ALTER TABLE order_items ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]:
        _ensure_pg_column(conn, 'order_items', column, ddl)

    _safe_pg_execute(conn, """
        CREATE TABLE IF NOT EXISTS operations (
            id SERIAL PRIMARY KEY,
            order_id INTEGER,
            user_id INTEGER,
            manager_id INTEGER,
            action_type TEXT NOT NULL,
            amount REAL DEFAULT 0,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, "create operations")
    for column, ddl in [
        ('order_id', "ALTER TABLE operations ADD COLUMN order_id INTEGER"),
        ('user_id', "ALTER TABLE operations ADD COLUMN user_id INTEGER"),
        ('manager_id', "ALTER TABLE operations ADD COLUMN manager_id INTEGER"),
        ('action_type', "ALTER TABLE operations ADD COLUMN action_type TEXT"),
        ('amount', "ALTER TABLE operations ADD COLUMN amount REAL DEFAULT 0"),
        ('details', "ALTER TABLE operations ADD COLUMN details TEXT"),
        ('created_at', "ALTER TABLE operations ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]:
        _ensure_pg_column(conn, 'operations', column, ddl)

    _safe_pg_execute(conn, """
        CREATE TABLE IF NOT EXISTS order_history (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            user_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, "create order_history")
    for column, ddl in [
        ('order_id', "ALTER TABLE order_history ADD COLUMN order_id INTEGER"),
        ('action', "ALTER TABLE order_history ADD COLUMN action TEXT"),
        ('details', "ALTER TABLE order_history ADD COLUMN details TEXT"),
        ('user_id', "ALTER TABLE order_history ADD COLUMN user_id INTEGER"),
        ('timestamp', "ALTER TABLE order_history ADD COLUMN timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]:
        _ensure_pg_column(conn, 'order_history', column, ddl)

    _safe_pg_execute(conn, """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """, "create settings")
    _safe_pg_execute(conn, "INSERT INTO settings (key, value) VALUES ('twilio_sid', '') ON CONFLICT (key) DO NOTHING", "seed twilio_sid")
    _safe_pg_execute(conn, "INSERT INTO settings (key, value) VALUES ('twilio_token', '') ON CONFLICT (key) DO NOTHING", "seed twilio_token")
    _safe_pg_execute(conn, "INSERT INTO settings (key, value) VALUES ('twilio_from', '') ON CONFLICT (key) DO NOTHING", "seed twilio_from")


def _init_sqlite(conn):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'gerant',
            manager_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            pickup_code TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            article_type TEXT,
            service_type TEXT,
            is_high_value INTEGER DEFAULT 0,
            base_price REAL DEFAULT 0,
            final_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0,
            price_overridden INTEGER DEFAULT 0,
            deposit_date TEXT NOT NULL,
            expected_pickup_date TEXT NOT NULL,
            actual_pickup_date TEXT,
            status TEXT NOT NULL DEFAULT 'received',
            global_status TEXT DEFAULT 'received',
            authorized_person_name TEXT,
            authorized_person_relation TEXT,
            article_photo TEXT,
            notes TEXT,
            created_by INTEGER,
            manager_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            article_type TEXT NOT NULL,
            service_type TEXT NOT NULL,
            is_high_value INTEGER DEFAULT 0,
            base_price REAL DEFAULT 0,
            final_price REAL DEFAULT 0,
            price_overridden INTEGER DEFAULT 0,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'received',
            marked_ready_by INTEGER,
            marked_ready_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            user_id INTEGER,
            manager_id INTEGER,
            action_type TEXT NOT NULL,
            amount REAL DEFAULT 0,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            user_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        INSERT OR IGNORE INTO settings VALUES ('twilio_sid', '');
        INSERT OR IGNORE INTO settings VALUES ('twilio_token', '');
        INSERT OR IGNORE INTO settings VALUES ('twilio_from', '');
    ''')
    conn.commit()

    sqlite_migrations = {
        'users': [
            ('manager_id', 'ALTER TABLE users ADD COLUMN manager_id INTEGER'),
            ('created_at', 'ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ],
        'orders': [
            ('total_price', 'ALTER TABLE orders ADD COLUMN total_price REAL DEFAULT 0'),
            ('global_status', "ALTER TABLE orders ADD COLUMN global_status TEXT DEFAULT 'received'"),
            ('created_by', 'ALTER TABLE orders ADD COLUMN created_by INTEGER'),
            ('manager_id', 'ALTER TABLE orders ADD COLUMN manager_id INTEGER'),
            ('updated_at', 'ALTER TABLE orders ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ],
        'order_items': [
            ('status', "ALTER TABLE order_items ADD COLUMN status TEXT DEFAULT 'received'"),
            ('marked_ready_by', 'ALTER TABLE order_items ADD COLUMN marked_ready_by INTEGER'),
            ('marked_ready_at', 'ALTER TABLE order_items ADD COLUMN marked_ready_at TIMESTAMP'),
            ('created_at', 'ALTER TABLE order_items ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ],
        'operations': [
            ('order_id', 'ALTER TABLE operations ADD COLUMN order_id INTEGER'),
            ('user_id', 'ALTER TABLE operations ADD COLUMN user_id INTEGER'),
            ('manager_id', 'ALTER TABLE operations ADD COLUMN manager_id INTEGER'),
            ('action_type', 'ALTER TABLE operations ADD COLUMN action_type TEXT'),
            ('amount', 'ALTER TABLE operations ADD COLUMN amount REAL DEFAULT 0'),
            ('details', 'ALTER TABLE operations ADD COLUMN details TEXT'),
            ('created_at', 'ALTER TABLE operations ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ],
        'order_history': [
            ('user_id', 'ALTER TABLE order_history ADD COLUMN user_id INTEGER'),
        ],
    }
    for table, migrations in sqlite_migrations.items():
        for column, ddl in migrations:
            _ensure_sqlite_column(conn, table, column, ddl)


# ── Initialisation publique ─────────────────────────────────────
def init_db():
    conn = get_db()
    try:
        if DATABASE_URL:
            _init_postgres(conn)
        else:
            _init_sqlite(conn)
    finally:
        conn.close()
    print("Base de données initialisée.")
