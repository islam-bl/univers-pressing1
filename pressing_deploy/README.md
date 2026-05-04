# Univers Pressing v2 — Application de Gestion

## Lancement rapide

```bash
# 1. Créer environnement virtuel
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 2. Installer dépendances
pip install -r requirements.txt

# 3. Lancer
python app.py

# 4. Ouvrir
http://127.0.0.1:5000
```

## Premier démarrage

```bash
python seed_data.py
# → Crée l'utilisateur: gerant / pressing2024
```

## Structure MVC
```
pressing_v2/
├── app.py                    # Application Flask
├── models/
│   ├── database.py           # Connexion SQLite
│   ├── user.py               # Classe User
│   ├── order.py              # Classe Order
│   └── catalog.py            # Catalogue des prix
├── controllers/
│   ├── auth_controller.py    # Login/Register/Logout
│   ├── order_controller.py   # CRUD commandes
│   └── sms_controller.py     # Twilio + WhatsApp
├── views/templates/
│   ├── login.html            # Page de connexion
│   └── index.html            # Application principale
└── static/
    ├── css/main.css
    ├── js/app.js + catalog_data.js
    └── images/logo.png
```

## Connexion Twilio (optionnel)
Aller dans Réglages → saisir Account SID, Auth Token, Numéro.
Sans Twilio: utiliser le bouton WhatsApp / Copier généré automatiquement.
