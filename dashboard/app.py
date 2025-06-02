from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from database import ParkingDatabase
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'parking_management_secret'
socketio = SocketIO(app)
db = ParkingDatabase()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parking_stats')
def get_parking_stats():
    # Get current occupancy
    occupied_spaces = db.get_current_occupancy()
    
    # Get today's revenue
    today = datetime.now().date()
    revenue = db.get_daily_revenue(today)
    
    # Get recent activities
    recent_activities = db.get_recent_activities(limit=5)
    
    # Get unauthorized attempts
    unauthorized_attempts = db.get_unauthorized_attempts(limit=5)
    
    return jsonify({
        'occupancy': occupied_spaces,
        'revenue': revenue,
        'recent_activities': recent_activities,
        'unauthorized_attempts': unauthorized_attempts
    })

@app.route('/api/hourly_stats')
def get_hourly_stats():
    # Get hourly statistics for the past 24 hours
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    hourly_data = db.get_hourly_statistics(yesterday, now)
    
    return jsonify(hourly_data)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

def emit_update(event_type, data):
    socketio.emit('update', {
        'type': event_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000) 