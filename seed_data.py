"""Données de test — exécuté au démarrage Railway via Procfile."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from models.database import init_db
from models.user import User
from models.order import Order


def seed():
    init_db()
    if not User.username_exists('gerant'):
        User.create('gerant', 'pressing2024', 'Rabia Abderrahmane', 'gerant')
        print("Utilisateur créé: gerant / pressing2024")
    else:
        print("Utilisateur 'gerant' existe déjà")

    # Récupérer l'id du gérant
    from models.database import get_db, DATABASE_URL
    PH = '%s' if DATABASE_URL else '?'
    conn = get_db()
    if DATABASE_URL:
        c = conn.cursor(); c.execute(f"SELECT id FROM users WHERE username={PH}", ('gerant',))
        row = c.fetchone(); c.close()
    else:
        row = conn.execute(f"SELECT id FROM users WHERE username={PH}", ('gerant',)).fetchone()
    conn.close()
    gerant_id = row['id'] if row else 1

    # Données test : seulement si la table orders est vide
    conn = get_db()
    if DATABASE_URL:
        c = conn.cursor(); c.execute("SELECT COUNT(*) AS n FROM orders")
        n = c.fetchone()['n']; c.close()
    else:
        n = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()['n']
    conn.close()
    if n and n > 0:
        print(f"{n} commande(s) déjà présentes — pas de données test ajoutées.")
        return

    from datetime import datetime, timedelta
    today = datetime.now()
    samples = [
        {
            'data': {
                'customer_name': 'Mohammed Alami',
                'customer_phone': '0662778092',
                'deposit_date': (today - timedelta(days=2)).strftime('%Y-%m-%d'),
                'expected_pickup_date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
                'notes': 'Costume bleu marine',
            },
            'items': [
                {'article_type': 'costume',  'service_type': 'nettoyage'},
                {'article_type': 'chemise',  'service_type': 'repassage'},
            ],
        },
        {
            'data': {
                'customer_name': 'Fatima Benali',
                'customer_phone': '0661234567',
                'deposit_date': (today - timedelta(days=1)).strftime('%Y-%m-%d'),
                'expected_pickup_date': (today + timedelta(days=2)).strftime('%Y-%m-%d'),
                'notes': '',
            },
            'items': [
                {'article_type': 'djellaba', 'service_type': 'repassage'},
            ],
        },
    ]
    for s in samples:
        o = Order.create(s['data'], s['items'], None, user_id=gerant_id, manager_id=gerant_id)
        print(f"Commande créée: {o['order_number']} — Code: {o['pickup_code']} — {o['items_count']} article(s)")

    print("\nDone! Connectez-vous avec: gerant / pressing2024")


if __name__ == '__main__':
    seed()
