"""
Initialisation et accès à la base de données.
- Supporte SQLite (local) et PostgreSQL (Railway via DATABASE_URL).
- Crée les tables si elles n'existent pas.
- Applique les migrations légères (ajout de colonnes / nouvelles tables) sans
  casser les données déjà présentes en production.
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
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'pressing.db')
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


# ── Helpers de migration légère ─────────────────────────────────
def _pg_column_exists(c, table, column):
    c.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name=%s AND column_name=%s
    """, (table, column))
    return c.fetchone() is not None


def _sqlite_column_exists(conn, table, column):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def init_db():
    conn = get_db()
    if DATABASE_URL:
        c = conn.cursor()
        # ── users ────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'gerant',
                manager_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        if not _pg_column_exists(c, 'users', 'manager_id'):
            c.execute('ALTER TABLE users ADD COLUMN manager_id INTEGER')

        # ── orders ───────────────────────────────────────────
        c.execute('''
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
        ''')
        for col, ddl in [
            ('total_price',   'ALTER TABLE orders ADD COLUMN total_price REAL DEFAULT 0'),
            ('global_status', "ALTER TABLE orders ADD COLUMN global_status TEXT DEFAULT 'received'"),
            ('manager_id',    'ALTER TABLE orders ADD COLUMN manager_id INTEGER'),
        ]:
            if not _pg_column_exists(c, 'orders', col):
                c.execute(ddl)

        # ── order_items (NOUVEAU) ────────────────────────────
        c.execute('''
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
        ''')

        # ── operations (journal des actions employés) ────────
        c.execute('''
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
        ''')

        # ── order_history ────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS order_history (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        if not _pg_column_exists(c, 'order_history', 'user_id'):
            c.execute('ALTER TABLE order_history ADD COLUMN user_id INTEGER')

        # ── settings ─────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        c.execute("INSERT INTO settings (key, value) VALUES ('twilio_sid', '') ON CONFLICT (key) DO NOTHING")
        c.execute("INSERT INTO settings (key, value) VALUES ('twilio_token', '') ON CONFLICT (key) DO NOTHING")
        c.execute("INSERT INTO settings (key, value) VALUES ('twilio_from', '') ON CONFLICT (key) DO NOTHING")

        conn.commit()
        c.close()
        conn.close()
    else:
        # ── SQLite ────────────────────────────────────────────
        c = conn.cursor()
        c.executescript('''
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
        # Migrations légères SQLite (en cas de base existante)
        for table, col, ddl in [
            ('users',         'manager_id',   'ALTER TABLE users ADD COLUMN manager_id INTEGER'),
            ('orders',        'total_price',  'ALTER TABLE orders ADD COLUMN total_price REAL DEFAULT 0'),
            ('orders',        'global_status',"ALTER TABLE orders ADD COLUMN global_status TEXT DEFAULT 'received'"),
            ('orders',        'manager_id',   'ALTER TABLE orders ADD COLUMN manager_id INTEGER'),
            ('order_history', 'user_id',      'ALTER TABLE order_history ADD COLUMN user_id INTEGER'),
        ]:
            try:
                if not _sqlite_column_exists(conn, table, col):
                    conn.execute(ddl)
            except Exception:
                pass
        conn.commit()
        conn.close()
    print("Base de données initialisée.")
