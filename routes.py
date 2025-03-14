from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, login_user, logout_user, current_user
from models import db, User, Match, Prediction, init_db
from utils import save_or_update_prediction, lock_predictions, datetimeformat, TBA_API_KEY, TBA_HEADERS, CURRENT_EVENT
import requests
from datetime import datetime

routes_bp = Blueprint('routes', __name__)


# Routes
@routes_bp.route('/')
def home():
    return render_template('home.html')

@routes_bp.route('/promote_admin/<int:user_id>', methods=['GET', 'POST'])
@login_required
def promote_admin(user_id):
    # Check if the current user is an admin
    if not current_user.is_admin and current_user.id != 1:
        flash("Only admins can promote other users to admin.")
        return redirect(url_for('routes.dashboard'))

    # Find the user to promote
    user_to_promote = User.query.get_or_404(user_id)
    
    # Prevent self-demotion or redundant promotion
    #if user_to_promote == current_user:
    #    flash("You cannot modify your own admin status this way.")
    #    return redirect(url_for('routes.dashboard'))
    if user_to_promote.is_admin:
        flash(f"{user_to_promote.username} is already an admin.")
        return redirect(url_for('routes.dashboard'))

    # Promote the user
    user_to_promote.is_admin = True
    db.session.commit()
    flash(f"{user_to_promote.username} has been promoted to admin.")
    return redirect(url_for('routes.dashboard'))

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
    users = User.query.all()
    matches = Match.query.order_by(Match.match_number.asc()).all()

    for match in matches:
        match.is_locked = lock_predictions(match)

    predictions = Prediction.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', matches=matches, predictions=predictions, users=users)

@routes_bp.route('/predict', methods=['POST'])
@login_required
def predict():
    match_id, winner = request.form['match_id'], request.form['predicted_winner']

    # Fetch the match to check its scheduled time
    pred = Prediction.query.filter_by(user_id=current_user.id, match_id=match_id).first()
    match = Match.query.get_or_404(match_id)
    success = save_or_update_prediction(current_user.id, match_id, winner)
    flash(f"{'Updated' if pred else 'Saved'} prediction!")
    return redirect(url_for('routes.dashboard', _anchor=f'match-{match_id}'))

@routes_bp.route('/update_scores')
@login_required
def update_scores():
    if not current_user.is_admin:
        flash("Admin privileges required to update scores.")
        return redirect(url_for('routes.dashboard'))
    current_time = datetime.utcnow().timestamp()

    unscored = Match.query.filter_by(scored=False).filter(Match.scheduled_time < current_time).all()
    updated = False
    for match in unscored:
        if not match.winner:
            key = f"{CURRENT_EVENT}_qm{match.match_number}"
            resp = requests.get(f'https://www.thebluealliance.com/api/v3/match/{key}', headers=TBA_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                # Only set winner if the match has a result; otherwise, leave it unset
                if data['actual_time']:  # Check if the match has been played (actual_time is set)
                    match.winner = "Tie" if data['winning_alliance'] == "" else data['winning_alliance'].capitalize()
                else:
                    continue  # Skip to next match if it hasn't been played yet

        # Process predictions only if a winner has been set
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
@login_required
def sync_matches():
    if not current_user.is_admin:
        flash("Admin privileges required to sync matches.")
        return redirect(url_for('routes.dashboard'))

    url = f'https://www.thebluealliance.com/api/v3/event/{CURRENT_EVENT}/matches/simple'
    resp = requests.get(url, headers=TBA_HEADERS)
    if resp.status_code != 200:
        flash("Failed to sync matches.")
        return redirect(url_for('routes.dashboard'))
    matches = resp.json() or []

    # Delete dependent predictions first, then matches
    db.session.query(Prediction).delete()
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
    if not current_user.is_admin:
        flash("Admin privileges required to reset scores.")
        return redirect(url_for('routes.dashboard'))

    for match in Match.query.all(): match.scored = False
    for match in Match.query.all(): match.winner = None
    for user in User.query.all(): user.points = 0
    db.session.commit()
    flash("Reset scores and points.")
    return redirect(url_for('routes.dashboard'))

@routes_bp.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.points.desc()).all()

    for user in users:
        # Total predictions for scored matches only
        total_scored_predictions = db.session.query(Prediction).\
            join(Match, Prediction.match_id == Match.id).\
            filter(Prediction.user_id == user.id, Match.scored == True).\
            count()

        # Correct predictions for scored matches
        correct_predictions = db.session.query(Prediction).\
            join(Match, Prediction.match_id == Match.id).\
            filter(Prediction.user_id == user.id, 
                   Prediction.predicted_winner == Match.winner, 
                   Match.scored == True).\
            count()

        # Calculate percentage (avoid division by zero)
        user.total_predictions = total_scored_predictions
        user.correct_predictions = correct_predictions
        user.percentage = (correct_predictions / total_scored_predictions * 100) if total_scored_predictions > 0 else 0

    return render_template('leaderboard.html', users=users)

@routes_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.home'))

def init_routes(app):
    # init_db(app)
    app.register_blueprint(routes_bp)