import pytz
from datetime import datetime, timedelta
from flask_login import current_user
from flask import flash
from models import db, Match, Prediction, User
import requests

TBA_API_KEY = 'KbhtQ7hLnAVrhwv4aAuXmZoREyhy0Dutxx5Xob4gHnlbmEUhO087gT253BBjk52n'  # Replace with your TBA API key
TBA_HEADERS = {'X-TBA-Auth-Key': TBA_API_KEY}
CURRENT_EVENT = '2025mimtp'

def lock_predictions(match, minutes_before=10):

    if match.scheduled_time is None:
        return False

    """Check if predictions should be locked based on scheduled time."""
    current_time = datetime.utcnow().timestamp()
    lock_time = match.scheduled_time - (minutes_before * 60)
    return current_time >= lock_time

def save_or_update_prediction(user_id, match_id, predicted_winner):
    """Save or update a user's prediction for a match."""
    match = Match.query.get(match_id)
    if not match:
        flash("Match not found.")
        return False
    
    if lock_predictions(match):
        flash(f"Predictions for match {match.match_number} are locked (less than 10 minutes until start).")
        return False
    
    pred = Prediction.query.filter_by(user_id=user_id, match_id=match_id).first()
    if pred:
        pred.predicted_winner = predicted_winner
        flash("Updated prediction!")
    else:
        db.session.add(Prediction(user_id=user_id, match_id=match_id, predicted_winner=predicted_winner))
        flash("Saved prediction!")
    db.session.commit()
    return True


def datetimeformat(value, format='%B %d, %Y'):
    if not value:
        return ''
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')  # For string timestamps
    elif isinstance(value, int):  # Handle Unix timestamp from TBA
        value = datetime.fromtimestamp(value)
    return value.strftime(format)