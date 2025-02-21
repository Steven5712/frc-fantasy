from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, login_user, logout_user, current_user
from models import db, User, Match, Prediction, init_db
from utils import datetimeformat, TBA_API_KEY, TBA_HEADERS, CURRENT_EVENT
import requests
from datetime import datetime

routes_bp = Blueprint('routes', __name__)


# Routes
@routes_bp.route('/')
def home():
    return render_template('home.html')

@routes_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username exists.')
            return redirect(url_for('routes.register'))
        user = User(username=username, password=password)  # Hash in production!
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('routes.login'))
    return render_template('register.html')

@routes_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:  # Hash check in production!
            login_user(user)
            return redirect(url_for('routes.dashboard'))
        flash('Invalid credentials.')
    return render_template('login.html')

@routes_bp.route('/dashboard')
@login_required
def dashboard():
    matches = Match.query.order_by(Match.match_number.asc()).all()
    predictions = Prediction.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', matches=matches, predictions=predictions)

@routes_bp.route('/predict', methods=['POST'])
@login_required
def predict():
    match_id, winner = request.form['match_id'], request.form['predicted_winner']
    pred = Prediction.query.filter_by(user_id=current_user.id, match_id=match_id).first()
    if pred:
        pred.predicted_winner = winner
    else:
        db.session.add(Prediction(user_id=current_user.id, match_id=match_id, predicted_winner=winner))
    db.session.commit()
    flash(f"{'Updated' if pred else 'Saved'} prediction!")
    return redirect(url_for('routes.dashboard', _anchor=f'match-{match_id}'))

@routes_bp.route('/update_scores')
def update_scores():
    unscored = Match.query.filter_by(scored=False).all()
    updated = False
    for match in unscored:
        if not match.winner:
            key = f"{CURRENT_EVENT}_qm{match.match_number}"
            resp = requests.get(f'https://www.thebluealliance.com/api/v3/match/{key}', headers=TBA_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                match.winner = "Tie" if data['winning_alliance'] == "" else data['winning_alliance'].capitalize()
        if match.winner:
            for pred in Prediction.query.filter_by(match_id=match.id).all():
                if match.winner != "Tie" and pred.predicted_winner == match.winner:
                    user = User.query.get(pred.user_id)
                    user.points = user.points or 0
                    user.points += 1
                    updated = True
            match.scored = True
    if updated:
        db.session.commit()
        flash("Scores updated!")
    else:
        flash("No new scores.")
    return redirect(url_for('routes.dashboard'))

@routes_bp.route('/sync_matches')
def sync_matches():
    url = f'https://www.thebluealliance.com/api/v3/event/{CURRENT_EVENT}/matches/simple'
    resp = requests.get(url, headers=TBA_HEADERS)
    if resp.status_code != 200:
        flash("Failed to sync matches.")
        return redirect(url_for('routes.dashboard'))
    matches = resp.json() or []
    Match.query.delete()
    db.session.commit()
    now = datetime.utcnow().timestamp()
    for m in [m for m in matches if m['comp_level'] == 'qm']:
        print(f"Match {m['match_number']}: predicted_time={m['predicted_time']}, actual_time={m['actual_time']}")
        red, blue = m['alliances']['red']['team_keys'], m['alliances']['blue']['team_keys']
        match = Match(
            red_team1=red[0], red_team2=red[1], red_team3=red[2],
            blue_team1=blue[0], blue_team2=blue[1], blue_team3=blue[2],
            match_number=m['match_number'], scheduled_time=m['predicted_time'] or m['actual_time'], scored=False
        )
        if m['actual_time'] and m['actual_time'] < now:
            match.winner, match.scored = ("Tie" if m['winning_alliance'] == "" else m['winning_alliance'].capitalize()), True
        db.session.add(match)
    db.session.commit()
    flash(f"Synced {len(matches)} matches!")
    return redirect(url_for('routes.dashboard'))

@routes_bp.route('/reset_scores')
@login_required
def reset_scores():
    for match in Match.query.all(): match.scored = False
    for user in User.query.all(): user.points = 0
    db.session.commit()
    flash("Reset scores and points.")
    return redirect(url_for('routes.dashboard'))

@routes_bp.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.points.desc()).all()
    return render_template('leaderboard.html', users=users)

@routes_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.home'))

def init_routes(app):
    init_db(app)
    app.register_blueprint(routes_bp)