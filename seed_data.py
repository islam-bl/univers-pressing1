"""Données de test — python seed_data.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from models.database import init_db
from models.user import User
from models.order import Order

def seed():
    init_db()
    # Créer utilisateur par défaut
    if not User.username_exists('gerant'):
        User.create('gerant', 'pressing2024', 'Rabia Abderrahmane', 'gerant')
        print("Utilisateur créé: gerant / pressing2024")
    else:
        print("Utilisateur 'gerant' existe déjà")
    # Données test
    from datetime import datetime, timedelta
    today = datetime.now()
    tests = [
        {'customer_name':'Mohammed Alami','customer_phone':'0662778092','article_type':'costume','service_type':'nettoyage','is_high_value':'0','deposit_date':(today-timedelta(days=2)).strftime('%Y-%m-%d'),'expected_pickup_date':(today+timedelta(days=1)).strftime('%Y-%m-%d'),'notes':'Costume bleu marine'},
        {'customer_name':'Fatima Benali','customer_phone':'0661234567','article_type':'djellaba','service_type':'repassage','is_high_value':'0','deposit_date':(today-timedelta(days=1)).strftime('%Y-%m-%d'),'expected_pickup_date':(today+timedelta(days=2)).strftime('%Y-%m-%d'),'notes':''},
    ]
    for t in tests:
        t['final_price'] = '0'
        t['price_overridden'] = '0'
        o = Order.create(t, None, 1)
        print(f"Commande créée: {o['order_number']} — Code: {o['pickup_code']}")
    print("\nDone! Connectez-vous avec: gerant / pressing2024")

if __name__ == '__main__':
    seed()
