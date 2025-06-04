import os
from flask import Flask
from config import Config
from models import db

app = Flask(__name__, template_folder='.', static_folder='.')

# Charger la configuration à partir des variables d'environnement
app.config.from_object(Config)
# Surcharger SQLALCHEMY_DATABASE_URI avec la variable d'environnement si elle existe
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', app.config['SQLALCHEMY_DATABASE_URI'])

db.init_app(app)

with app.app_context():
    db.create_all()  # Crée les tables si elles n'existent pas

from routes import *  # Importer les routes après avoir défini app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
