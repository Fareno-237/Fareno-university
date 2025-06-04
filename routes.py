from app import app
from flask import request, jsonify, send_file
from models import db, Utilisateur, Enseignant, Salle, Groupe, Matiere, Contrainte, EmploiDuTemps, Log
import jwt
import datetime
from functools import wraps
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from icalendar import Calendar, Event

# Route pour l'URL racine
@app.route('/')
def index():
    return send_file('index.html')

# Route pour la page de connexion
@app.route('/login')
def login_page():
    return send_file('login.html')

# Middleware pour vérifier le token JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token manquant'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = Utilisateur.query.get(data['id_utilisateur'])  # Ajusté pour id_utilisateur
        except:
            return jsonify({'message': 'Token invalide'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# Login API
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    mot_de_passe = data.get('mot_de_passe')
    
    user = Utilisateur.query.filter_by(email=email).first()
    if not user or user.mot_de_passe != mot_de_passe:
        return jsonify({'message': 'Identifiants incorrects'}), 401
    
    user.derniere_connexion = datetime.datetime.utcnow()
    db.session.commit()
    
    token = jwt.encode({
        'id_utilisateur': user.id_utilisateur,  # Ajusté pour id_utilisateur
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'])
    
    return jsonify({'token': token, 'role': user.role})

# Gestion des utilisateurs
@app.route('/api/utilisateurs', methods=['GET'])
@token_required
def get_utilisateurs(current_user):
    utilisateurs = Utilisateur.query.all()
    return jsonify([{
        'nom': f"{u.nom} {u.prenom}",
        'email': u.email,
        'role': u.role
    } for u in utilisateurs])

@app.route('/api/utilisateurs', methods=['POST'])
@token_required
def add_utilisateur(current_user):
    data = request.get_json()
    nouvel_utilisateur = Utilisateur(
        nom=data['nom'],
        prenom=data['prenom'],
        email=data['email'],
        mot_de_passe=data['mot_de_passe'],
        role=data.get('role', 'enseignant')
    )
    db.session.add(nouvel_utilisateur)
    db.session.commit()
    
    log = Log(action="Ajout d'utilisateur", details=f"Ajout de {data['nom']} {data['prenom']}")
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Utilisateur ajouté'})

# Gestion des ressources
@app.route('/api/enseignants', methods=['GET'])
@token_required
def get_enseignants(current_user):
    enseignants = Enseignant.query.all()
    return jsonify([{
        'nom': f"{e.nom} {e.prenom}",
        'email': e.email,
        'matieres': [matiere.nom for matiere in e.matieres],
        'disponibilites': e.disponibilites
    } for e in enseignants])

@app.route('/api/enseignants', methods=['POST'])
@token_required
def add_enseignant(current_user):
    data = request.get_json()
    nouvel_enseignant = Enseignant(
        nom=data['nom'],
        prenom=data['prenom'],
        email=data['email'],
        disponibilites=data.get('disponibilites')
    )
    db.session.add(nouvel_enseignant)
    db.session.commit()
    return jsonify({'message': 'Enseignant ajouté'})

@app.route('/api/salles', methods=['GET'])
@token_required
def get_salles(current_user):
    salles = Salle.query.all()
    return jsonify([{
        'nom': s.nom,
        'capacite': s.capacite,
        'equipements': s.equipements
    } for s in salles])

@app.route('/api/groupes', methods=['GET'])
@token_required
def get_groupes(current_user):
    groupes = Groupe.query.all()
    return jsonify([{
        'nom': g.nom,
        'nombre_etudiants': g.nombre_etudiants,
        'matieres': [matiere.nom for matiere in g.matieres]
    } for g in groupes])

# Saisie des contraintes
@app.route('/api/contraintes', methods=['POST'])
@token_required
def add_contrainte(current_user):
    data = request.get_json()
    nouvelle_contrainte = Contrainte(
        type_contrainte=data['type'],
        valeur=data['valeur'],
        entite_concernee=data['entite'],
        id_entite=data['id_entite']
    )
    db.session.add(nouvelle_contrainte)
    db.session.commit()
    return jsonify({'message': 'Contrainte ajoutée'})

# Visualisation
@app.route('/api/emplois', methods=['GET'])
@token_required
def get_emplois(current_user):
    groupe_id = request.args.get('id_groupe')  # Ajusté pour id_groupe
    enseignant_id = request.args.get('id_enseignant')  # Ajusté pour id_enseignant
    date = request.args.get('date')
    
    query = EmploiDuTemps.query
    if groupe_id:
        query = query.filter_by(id_groupe=groupe_id)
    if enseignant_id:
        query = query.filter_by(id_enseignant=enseignant_id)
    if date:
        query = query.filter_by(jour=date)
    
    emplois = query.all()
    return jsonify([{
        'heure': f"{e.heure_debut} - {e.heure_fin}",
        'jour': e.jour.strftime('%A'),
        'matiere': Matiere.query.get(e.id_matiere).nom,
        'enseignant': Enseignant.query.get(e.id_enseignant).nom + ' ' + Enseignant.query.get(e.id_enseignant).prenom
    } for e in emplois])

# Exportation (PDF comme exemple)
@app.route('/api/export/pdf', methods=['GET'])
@token_required
def export_pdf(current_user):
    groupe_id = request.args.get('id_groupe')  # Ajusté pour id_groupe
    emplois = EmploiDuTemps.query.filter_by(id_groupe=groupe_id).all()
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Emploi du Temps - FARENO UNIVERSITY")
    y = 700
    for e in emplois:
        c.drawString(100, y, f"{e.jour} {e.heure_debut}-{e.heure_fin}: {Matiere.query.get(e.id_matiere).nom}")
        y -= 20
    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='emploi.pdf')

# Logs
@app.route('/api/logs', methods=['GET'])
@token_required
def get_logs(current_user):
    logs = Log.query.all()
    return jsonify([{
        'date': l.timestamp,
        'utilisateur': Utilisateur.query.get(current_user.id_utilisateur).nom,
        'action': l.action,
        'details': l.details
    } for l in logs])
