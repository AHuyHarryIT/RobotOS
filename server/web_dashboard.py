"""
Web Dashboard for RobotOS Command Monitoring
Provides real-time statistics and command history visualization
"""
import os
import sys
from flask import Flask, render_template, jsonify, request
from threading import Thread
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_aggregator import get_aggregator, CommandSource, CommandPriority
from config import RPI_IP, HEARTBEAT_PORT

app = Flask(__name__)

# Global state for heartbeat monitoring and ZMQ socket
last_heartbeat_time = None
rpi_connected = False
zmq_socket = None  # Will be set when dashboard is started

# Mode control state
current_mode = "idle"  # idle, sequence, controller, server
mode_active = False
sequence_input_queue = []  # Queue for sequence commands from web


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
    return render_template('index.html', rpi_host=RPI_IP)


@app.route('/api/stats')
def get_stats():
    """
    API endpoint to get current command statistics
    Returns JSON with total commands, by-source breakdown, and recent history
    """
    aggregator = get_aggregator()
    stats = aggregator.get_stats()
    
    # Get recent command history (last 20 commands)
    history = aggregator.get_recent_history(count=20)
    
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


@app.route('/api/control', methods=['POST'])
def control():
    """
    API endpoint to send control commands from web interface
    Accepts JSON with 'command' field
    Processes through aggregator and forwards to RPi
    """
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        
        if not command:
            return jsonify({'status': 'error', 'message': 'No command provided'}), 400
        
        # Get aggregator instance
        aggregator = get_aggregator()
        
        # Process command through aggregator
        success, processed_cmd, msg = aggregator.process_command(
            command=command,
            source=CommandSource.MANUAL,
            priority=CommandPriority.HIGH if command == 'stop' else CommandPriority.NORMAL
        )
        
        if success and processed_cmd:
            # Send to RPi if socket is available
            if zmq_socket:
                from zmq_client import send_command
                send_command(zmq_socket, processed_cmd)
                return jsonify({
                    'status': 'success',
                    'command': processed_cmd,
                    'original': command,
                    'message': msg
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'ZMQ socket not initialized. Start dashboard from main.py'
                }), 503
        else:
            return jsonify({
                'status': 'error',
                'message': msg
            }), 400
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/mode', methods=['GET'])
def get_mode():
    """Get current mode and status"""
    return jsonify({
        'mode': current_mode,
        'active': mode_active,
        'available_modes': ['idle', 'sequence', 'controller', 'server']
    })


@app.route('/api/mode/change', methods=['POST'])
def change_mode():
    """
    Change operation mode
    Modes: idle, sequence, controller, server
    """
    global current_mode, mode_active
    
    try:
        data = request.get_json()
        new_mode = data.get('mode', '').strip().lower()
        
        valid_modes = ['idle', 'sequence', 'controller', 'server']
        if new_mode not in valid_modes:
            return jsonify({
                'status': 'error',
                'message': f'Invalid mode. Must be one of: {valid_modes}'
            }), 400
        
        # Stop current mode if active
        if mode_active:
            mode_active = False
            time.sleep(0.5)  # Give time to stop
        
        # Set new mode
        current_mode = new_mode
        
        # Note: Actual mode execution should be handled by background threads
        # This just tracks the requested mode
        
        return jsonify({
            'status': 'success',
            'mode': current_mode,
            'message': f'Mode changed to {new_mode}'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/sequence', methods=['POST'])
def sequence_command():
    """
    Send command in sequence mode
    Adds command to queue for processing
    """
    global sequence_input_queue
    
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        
        if not command:
            return jsonify({'status': 'error', 'message': 'No command provided'}), 400
        
        # Add to sequence queue
        sequence_input_queue.append(command)
        
        # Also execute immediately if we have socket
        if zmq_socket:
            aggregator = get_aggregator()
            success, processed_cmd, msg = aggregator.process_command(
                command=command,
                source=CommandSource.MANUAL,
                priority=CommandPriority.NORMAL
            )
            
            if success and processed_cmd:
                from zmq_client import send_command
                send_command(zmq_socket, processed_cmd)
                return jsonify({
                    'status': 'success',
                    'command': processed_cmd,
                    'message': 'Command executed'
                })
        
        return jsonify({
            'status': 'success',
            'message': 'Command queued'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500



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
    print(f"🤖 Monitoring RPi: {RPI_IP}")
    print(f"{'='*60}\n")
    
    # Run Flask app
    app.run(host=host, port=port, debug=debug, threaded=True)


def run_dashboard_background(host='0.0.0.0', port=5000, sock=None):
    """
    Run the dashboard in a background thread
    Allows the dashboard to run alongside other client modes
    
    Args:
        host: Host IP to bind to
        port: Port to listen on
        sock: ZMQ socket for sending commands to RPi (optional)
    Returns:
        Thread object running the dashboard
    """
    global zmq_socket
    zmq_socket = sock  # Store socket for control endpoint
    app.start_time = time.time()
    
    dashboard_thread = Thread(
        target=lambda: app.run(host=host, port=port, debug=False, threaded=True),
        daemon=True,
        name="WebDashboard"
    )
    dashboard_thread.start()
    
    print(f"\n🌐 Web Dashboard started in background at http://{host}:{port}")
    if sock:
        print("📡 Web controls enabled - you can send commands from browser")
    else:
        print("⚠️  Web controls disabled - no ZMQ socket provided")
    return dashboard_thread


if __name__ == '__main__':
    # Run dashboard directly when script is executed
    run_dashboard(debug=True)
