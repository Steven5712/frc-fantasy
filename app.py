from flask import Flask
from flask_login import LoginManager
from models import db, User, Match, Prediction, init_db
from routes import init_routes
from utils import datetimeformat
from datetime import datetime
import os
from dotenv import load_dotenv

# Load .env file if it exists (optional for local dev)
load_dotenv()  # Safe to call; ignored if no .env file exists

# App Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'tbot4230'
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.jinja_env.filters['datetimeformat'] = datetimeformat

# Initialize database and routes
init_db(app)
init_routes(app)

login_manager = LoginManager(app)
login_manager.login_view = 'routes.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don’t exist (safe for RDS)
        # Only seed data if explicitly enabled via environment variable
        if os.getenv('SEED_DATA', 'false').lower() == 'true':
            if not Match.query.first():
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
    app.run(host="0.0.0.0", port=5000, debug=True)