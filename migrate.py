"""
Script de migration — à exécuter une seule fois sur Railway.
Lance avec : python migrate.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from models.database import get_db, DATABASE_URL

def migrate():
    print("Migration en cours...")
    conn = get_db()
    if DATABASE_URL:
        c = conn.cursor()
        # Créer la table operations si elle n'existe pas
        c.execute('''CREATE TABLE IF NOT EXISTS operations (
            id SERIAL PRIMARY KEY,
            order_id INTEGER,
            user_id INTEGER,
            manager_id INTEGER,
            action_type TEXT NOT NULL,
            amount REAL DEFAULT 0,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # Ajouter les colonnes manquantes dans orders
        for col, ddl in [
            ('global_status', "ALTER TABLE orders ADD COLUMN IF NOT EXISTS global_status TEXT DEFAULT 'received'"),
            ('total_price',   "ALTER TABLE orders ADD COLUMN IF NOT EXISTS total_price REAL DEFAULT 0"),
            ('manager_id',    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS manager_id INTEGER"),
            ('created_by',    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS created_by INTEGER"),
        ]:
            try:
                c.execute(ddl)
                print(f"  ✓ orders.{col}")
            except Exception as e:
                print(f"  - orders.{col} déjà présent ou erreur : {e}")
        # Ajouter les colonnes manquantes dans order_items
        for col, ddl in [
            ('marked_ready_by', "ALTER TABLE order_items ADD COLUMN IF NOT EXISTS marked_ready_by INTEGER"),
            ('marked_ready_at', "ALTER TABLE order_items ADD COLUMN IF NOT EXISTS marked_ready_at TIMESTAMP"),
        ]:
            try:
                c.execute(ddl)
                print(f"  ✓ order_items.{col}")
            except Exception as e:
                print(f"  - order_items.{col} déjà présent ou erreur : {e}")
        # Sync global_status avec status pour les anciennes commandes
        c.execute("UPDATE orders SET global_status = status WHERE global_status IS NULL OR global_status = ''")
        print(f"  ✓ global_status synchronisé")
        conn.commit()
        c.close()
    else:
        print("SQLite — pas de migration nécessaire.")
    conn.close()
    print("Migration terminée ✅")

if __name__ == '__main__':
    migrate()
