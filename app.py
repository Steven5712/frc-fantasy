from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from models import db, User, Match, Prediction
from routes import init_routes
from utils import datetimeformat
from datetime import datetime

# App Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'tbot4230'  # Change this to a random string
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fantasy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.jinja_env.filters['datetimeformat'] = datetimeformat

# Initialize routes
init_routes(app)

login_manager = LoginManager(app)
login_manager.login_view = 'routes.login'

# User Loader for LoginManager
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Creates the database tables
        if not Match.query.first():  # Only add if no matches exist
            match1 = Match(
                red_team1="Team 1234", red_team2="Team 2345", red_team3="Team 3456",
                blue_team1="Team 5678", blue_team2="Team 6789", blue_team3="Team 7890"
            )
            match2 = Match(
                red_team1="Team 9101", red_team2="Team 1012", red_team3="Team 1123",
                blue_team1="Team 2345", blue_team2="Team 3456", blue_team3="Team 4567"
            )
            db.session.add(match1)
            db.session.add(match2)
            db.session.commit()
        matches = Match.query.limit(5).all()  # First 5 matches
        for match in matches:
            match.winner = None
            match.scored = False
        db.session.commit()
    app.run(debug=True)