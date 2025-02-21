from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Import db from app.py
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    points = db.Column(db.Integer, default=0)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    red_team1 = db.Column(db.String(50), nullable=False)
    red_team2 = db.Column(db.String(50), nullable=False)
    red_team3 = db.Column(db.String(50), nullable=False)
    blue_team1 = db.Column(db.String(50), nullable=False)
    blue_team2 = db.Column(db.String(50), nullable=False)
    blue_team3 = db.Column(db.String(50), nullable=False)
    winner = db.Column(db.String(50))  # "Red" or "Blue" (or None if not yet decided)
    scored = db.Column(db.Boolean, default=False)
    match_number = db.Column(db.Integer)  # New: Qualification match number
    scheduled_time = db.Column(db.Integer)  # New: UNIX timestamp for scheduled start

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    predicted_winner = db.Column(db.String(50))

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()