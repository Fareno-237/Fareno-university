from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

# Charger les variables d'environnement du .env
load_dotenv()

# Initialisation de l'app Flask
app = Flask(__name__)
app.config.from_object("config.Config")

# Connexion à la base de données
db = SQLAlchemy(app)

# Importer routes et modèles après la création de l'app et db
import routes
import models
