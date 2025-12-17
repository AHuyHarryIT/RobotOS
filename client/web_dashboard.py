"""
Web Dashboard for RobotOS Command Monitoring
Provides real-time statistics and command history visualization
"""
import os
import sys
from flask import Flask, render_template, jsonify
from threading import Thread
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_aggregator import get_aggregator
from config import RPI_HOST, HEARTBEAT_PORT

app = Flask(__name__)

# Global state for heartbeat monitoring
last_heartbeat_time = None
rpi_connected = False


def update_heartbeat_status():
    """
    Monitor heartbeat status from RPi server
    Updates global connection status variables
    """
    global last_heartbeat_time, rpi_connected
    # This will be updated by the main client when receiving heartbeats
    # For now, we'll just track the status
    pass


@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html', rpi_host=RPI_HOST)


@app.route('/api/stats')
def get_stats():
    """
    API endpoint to get current command statistics
    Returns JSON with total commands, by-source breakdown, and recent history
    """
    aggregator = get_aggregator()
    stats = aggregator.get_stats()
    
    # Get recent command history (last 20 commands)
    history = aggregator.get_recent_history(limit=20)
    
    # Calculate uptime (placeholder - would need actual tracking)
    uptime_seconds = int(time.time() - app.start_time) if hasattr(app, 'start_time') else 0
    uptime_str = format_uptime(uptime_seconds)
    
    return jsonify({
        'stats': stats,
        'history': history,
        'uptime': uptime_str,
        'rpi_connected': rpi_connected,
        'last_heartbeat': last_heartbeat_time,
        'timestamp': time.time()
    })


@app.route('/api/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'RobotOS Dashboard'})


def format_uptime(seconds):
    """
    Format uptime in human-readable format
    Args:
        seconds: Total seconds of uptime
    Returns:
        Formatted string (e.g., "2h 15m 30s")
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """
    Start the web dashboard server
    
    Args:
        host: Host IP to bind to (default: 0.0.0.0 for all interfaces)
        port: Port to listen on (default: 5000)
        debug: Enable Flask debug mode (default: False)
    """
    # Record start time for uptime calculation
    app.start_time = time.time()
    
    print(f"\n{'='*60}")
    print(f"🌐 RobotOS Web Dashboard Starting...")
    print(f"{'='*60}")
    print(f"📊 Dashboard URL: http://{host}:{port}")
    print(f"🤖 Monitoring RPi: {RPI_HOST}")
    print(f"{'='*60}\n")
    
    # Run Flask app
    app.run(host=host, port=port, debug=debug, threaded=True)


def run_dashboard_background(host='0.0.0.0', port=5000):
    """
    Run the dashboard in a background thread
    Allows the dashboard to run alongside other client modes
    
    Args:
        host: Host IP to bind to
        port: Port to listen on
    Returns:
        Thread object running the dashboard
    """
    app.start_time = time.time()
    
    dashboard_thread = Thread(
        target=lambda: app.run(host=host, port=port, debug=False, threaded=True),
        daemon=True,
        name="WebDashboard"
    )
    dashboard_thread.start()
    
    print(f"\n🌐 Web Dashboard started in background at http://{host}:{port}")
    return dashboard_thread


if __name__ == '__main__':
    # Run dashboard directly when script is executed
    run_dashboard(debug=True)
