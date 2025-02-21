import pytz
from datetime import datetime
from flask_login import current_user
import requests

TBA_API_KEY = 'KbhtQ7hLnAVrhwv4aAuXmZoREyhy0Dutxx5Xob4gHnlbmEUhO087gT253BBjk52n'  # Replace with your TBA API key
TBA_HEADERS = {'X-TBA-Auth-Key': TBA_API_KEY}
CURRENT_EVENT = '2024mndu2'

def datetimeformat(value, format='%B %d, %Y'):
    if not value:
        return ''
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')  # For string timestamps
    elif isinstance(value, int):  # Handle Unix timestamp from TBA
        value = datetime.fromtimestamp(value)
    return value.strftime(format)