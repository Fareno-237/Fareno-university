# routes.py
from app import app
from flask import request, jsonify, send_file
from models import db, Utilisateur, Enseignant, Salle, Groupe, Matiere, Contrainte, EmploiDuTemps, Log
import jwt
import datetime
from functools import wraps
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Accueil
@app.route('/')
def index():
    return send_file('index.html')

@app.route('/login')
def login_page():
    return send_file('login.html')

# Middleware JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token manquant'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = Utilisateur.query.get(data['id_utilisateur'])
        except Exception as e:
            return jsonify({'message': 'Token invalide'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# Authentification
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    mot_de_passe = data.get('mot_de_passe')

    if not email or not mot_de_passe:
        return jsonify({'message': 'Champs requis manquants'}), 400

    user = Utilisateur.query.filter_by(email=email).first()
    if not user or user.mot_de_passe != mot_de_passe:
        return jsonify({'message': 'Identifiants incorrects'}), 401

    user.derniere_connexion = datetime.datetime.utcnow()
    db.session.commit()

    token = jwt.encode({
        'id_utilisateur': user.id_utilisateur,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'])

    return jsonify({'token': token, 'role': user.role})

# Utilisateurs
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
    try:
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ressources : Enseignants
@app.route('/api/enseignants', methods=['GET'])
@token_required
def get_enseignants(current_user):
    enseignants = Enseignant.query.all()
    return jsonify([{
        'nom': f"{e.nom} {e.prenom}",
        'email': e.email,
        'matieres': [m.nom for m in e.matieres],
        'disponibilites': e.disponibilites
    } for e in enseignants])

@app.route('/api/enseignants', methods=['POST'])
@token_required
def add_enseignant(current_user):
    data = request.get_json()
    try:
        nouvel_enseignant = Enseignant(
            nom=data['nom'],
            prenom=data['prenom'],
            email=data['email'],
            disponibilites=data.get('disponibilites')
        )
        db.session.add(nouvel_enseignant)
        db.session.commit()
        return jsonify({'message': 'Enseignant ajouté'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Salles et Groupes
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
        'matieres': [m.nom for m in g.matieres]
    } for g in groupes])

# Contraintes
@app.route('/api/contraintes', methods=['POST'])
@token_required
def add_contrainte(current_user):
    data = request.get_json()
    try:
        nouvelle_contrainte = Contrainte(
            type_contrainte=data['type'],
            valeur=data['valeur'],
            entite_concernee=data['entite'],
            id_entite=data['id_entite']
        )
        db.session.add(nouvelle_contrainte)
        db.session.commit()
        return jsonify({'message': 'Contrainte ajoutée'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Emplois du temps
@app.route('/api/emplois', methods=['GET'])
@token_required
def get_emplois(current_user):
    groupe_id = request.args.get('id_groupe')
    enseignant_id = request.args.get('id_enseignant')
    date = request.args.get('date')

    query = EmploiDuTemps.query
    if groupe_id:
        query = query.filter_by(id_groupe=groupe_id)
    if enseignant_id:
        query = query.filter_by(id_enseignant=enseignant_id)
    if date:
        query = query.filter_by(jour=date)

    emplois = query.all()
    matieres = {m.id_matiere: m.nom for m in Matiere.query.all()}
    enseignants = {e.id_enseignant: f"{e.nom} {e.prenom}" for e in Enseignant.query.all()}

    return jsonify([{
        'heure': f"{e.heure_debut} - {e.heure_fin}",
        'jour': e.jour.strftime('%A'),
        'matiere': matieres.get(e.id_matiere, 'Inconnu'),
        'enseignant': enseignants.get(e.id_enseignant, 'Inconnu')
    } for e in emplois])

# Export PDF
@app.route('/api/export/pdf', methods=['GET'])
@token_required
def export_pdf(current_user):
    groupe_id = request.args.get('id_groupe')
    emplois = EmploiDuTemps.query.filter_by(id_groupe=groupe_id).all()

    matieres = {m.id_matiere: m.nom for m in Matiere.query.all()}
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Emploi du Temps - FARENO UNIVERSITY")
    y = 700
    for e in emplois:
        jour = e.jour.strftime('%A %d/%m/%Y')
        ligne = f"{jour} {e.heure_debut}-{e.heure_fin}: {matieres.get(e.id_matiere, 'Inconnu')}"
        c.drawString(100, y, ligne)
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
        'date': l.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'utilisateur': f"{current_user.nom} {current_user.prenom}",
        'action': l.action,
        'details': l.details
    } for l in logs])
