from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Modèle Utilisateur
class Utilisateur(db.Model):
    __tablename__ = 'utilisateurs'
    id_utilisateur = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='enseignant', server_default='enseignant')
    derniere_connexion = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Utilisateur {self.email} - {self.role}>"

# Modèle Enseignant
class Enseignant(db.Model):
    __tablename__ = 'enseignants'
    id_enseignant = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    disponibilites = db.Column(db.JSON, nullable=True)
    preferences = db.Column(db.JSON, nullable=True)
    matieres = db.relationship('Matiere', secondary='enseignant_matiere', backref=db.backref('enseignants', lazy='dynamic'))

    def __repr__(self):
        return f"<Enseignant {self.nom} {self.prenom}>"

# Modèle Salle
class Salle(db.Model):
    __tablename__ = 'salles'
    id_salle = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    capacite = db.Column(db.Integer, nullable=False)

    # Utilisation ARRAY (PostgreSQL uniquement)
    equipements = db.Column(db.ARRAY(db.Text), nullable=True)
    # Si tu veux tester localement avec SQLite, commente la ligne ci-dessus et utilise :
    # equipements = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.CheckConstraint('capacite > 0', name='check_capacite_positive'),
    )

    def __repr__(self):
        return f"<Salle {self.nom} - Capacité {self.capacite}>"

# Modèle Groupe
class Groupe(db.Model):
    __tablename__ = 'groupes'
    id_groupe = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    nombre_etudiants = db.Column(db.Integer, nullable=False)
    matieres = db.relationship('Matiere', secondary='groupe_matiere', backref=db.backref('groupes', lazy='dynamic'))

    __table_args__ = (
        db.CheckConstraint('nombre_etudiants > 0', name='check_nombre_etudiants_positive'),
    )

    def __repr__(self):
        return f"<Groupe {self.nom} - {self.nombre_etudiants} étudiants>"

# Modèle Matiere
class Matiere(db.Model):
    __tablename__ = 'matieres'
    id_matiere = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    duree = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.CheckConstraint('duree > 0', name='check_duree_positive'),
    )

    def __repr__(self):
        return f"<Matiere {self.nom} - Durée {self.duree}h>"

# Table d'association Enseignant-Matiere
enseignant_matiere = db.Table('enseignant_matiere',
    db.Column('id_enseignant', db.Integer, db.ForeignKey('enseignants.id_enseignant'), primary_key=True),
    db.Column('id_matiere', db.Integer, db.ForeignKey('matieres.id_matiere'), primary_key=True)
)

# Table d'association Groupe-Matiere
groupe_matiere = db.Table('groupe_matiere',
    db.Column('id_groupe', db.Integer, db.ForeignKey('groupes.id_groupe'), primary_key=True),
    db.Column('id_matiere', db.Integer, db.ForeignKey('matieres.id_matiere'), primary_key=True)
)

# Modèle Contrainte
class Contrainte(db.Model):
    __tablename__ = 'contraintes'
    id_contrainte = db.Column(db.Integer, primary_key=True)
    type_contrainte = db.Column(db.String(50), nullable=False)
    valeur = db.Column(db.Text, nullable=False)
    entite_concernee = db.Column(db.String(20), nullable=False)
    id_entite = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.CheckConstraint("entite_concernee IN ('enseignant', 'groupe', 'salle')", name='check_entite_concernee'),
    )

    def __repr__(self):
        return f"<Contrainte {self.type_contrainte} sur {self.entite_concernee} {self.id_entite}>"

# Modèle EmploiDuTemps
class EmploiDuTemps(db.Model):
    __tablename__ = 'emplois_du_temps'
    id_emploi = db.Column(db.Integer, primary_key=True)
    id_enseignant = db.Column(db.Integer, db.ForeignKey('enseignants.id_enseignant'))
    id_groupe = db.Column(db.Integer, db.ForeignKey('groupes.id_groupe'))
    id_salle = db.Column(db.Integer, db.ForeignKey('salles.id_salle'))
    id_matiere = db.Column(db.Integer, db.ForeignKey('matieres.id_matiere'))
    jour = db.Column(db.Date, nullable=False)
    heure_debut = db.Column(db.Time, nullable=False)
    heure_fin = db.Column(db.Time, nullable=False)

    __table_args__ = (
        db.CheckConstraint('heure_fin > heure_debut', name='check_heure_fin'),
    )

    def __repr__(self):
        return f"<EDT {self.jour} - {self.heure_debut}-{self.heure_fin}>"

# Modèle Log
class Log(db.Model):
    __tablename__ = 'logs'
    id_log = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    details = db.Column(db.Text)
    conflit_resolu = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Log {self.timestamp} - {self.action}>"
