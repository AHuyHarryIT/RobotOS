"""
Web Dashboard for RobotOS Command Monitoring
Provides real-time statistics and command history visualization
"""
import os
import sys
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from command_aggregator import get_aggregator, CommandSource, CommandPriority
from config import RPI_IP, HEARTBEAT_PORT

app = Flask(__name__)
app.config['SECRET_KEY'] = 'robotos-secret-key-2025'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state for heartbeat monitoring and ZMQ socket
last_heartbeat_time = None
rpi_connected = False
zmq_socket = None  # Will be set when dashboard is started

# Controller state tracking
controller_connected = False
controller_name = None
controller_last_check = 0

# Mode control state
current_mode = "idle"  # idle, sequence, controller, server
mode_active = False
mode_thread = None  # Thread running the current mode
mode_stop_event = Event()  # Event to signal mode thread to stop
sequence_input_queue = []  # Queue for sequence commands from web

# Event for signaling updates
update_event = Event()
background_update_thread = None

DEBUG = os.getenv("DEBUG", "False").lower() == "true"


def periodic_dashboard_update():
    """Background thread to send periodic dashboard updates for uptime/heartbeat"""
    while True:
        time.sleep(5)  # Update every 5 seconds for uptime
        try:
            send_dashboard_update()
        except Exception as e:
            print(f"[Warning] Periodic update failed: {e}")

def controller_mode_thread():
    """Run controller mode loop"""
    global mode_active
    try:
        print("[Mode] Starting controller mode...")
        mode_active = True
        from controller_mode import controller_loop
        controller_loop(zmq_socket)
    except Exception as e:
        print(f"[Mode] Controller mode error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mode_active = False
        print("[Mode] Controller mode stopped")

def update_heartbeat_status():
    """
    Monitor heartbeat status from RPi server
    Updates global connection status variables
    """
    global last_heartbeat_time, rpi_connected
    # This will be updated by the main client when receiving heartbeats
    # For now, we'll just track the status
    pass


def check_controller_status():
    """
    Check if Xbox controller is connected
    Updates global controller_connected and controller_name
    Returns: True if connected, False otherwise
    """
    global controller_connected, controller_name, controller_last_check
    
    # Throttle checks to avoid overhead (max once per second)
    now = time.time()
    if now - controller_last_check < 1.0:
        return controller_connected
    
    controller_last_check = now
    
    try:
        import pygame
        if not pygame.get_init():
            pygame.init()
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        
        count = pygame.joystick.get_count()
        
        if count > 0:
            joy = pygame.joystick.Joystick(0)
            if not joy.get_init():
                joy.init()
            controller_connected = True
            controller_name = joy.get_name()
            return True
        else:
            controller_connected = False
            controller_name = None
            return False
            
    except Exception as e:
        controller_connected = False
        controller_name = None
        return False


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


# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"[WebSocket] Client connected: {request.sid}")
    # Send initial data on connect
    send_dashboard_update()


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"[WebSocket] Client disconnected: {request.sid}")


@socketio.on('request_update')
def handle_request_update():
    """Handle client request for dashboard update"""
    send_dashboard_update()


def send_dashboard_update():
    """Send dashboard data to all connected clients"""
    try:
        aggregator = get_aggregator()
        stats = aggregator.get_stats()
        history = aggregator.get_recent_history(count=20)
        uptime_seconds = int(time.time() - app.start_time) if hasattr(app, 'start_time') else 0
        uptime_str = format_uptime(uptime_seconds)
        
        # Check controller status
        check_controller_status()
        
        data = {
            'stats': stats,
            'history': history,
            'uptime': uptime_str,
            'rpi_connected': rpi_connected,
            'last_heartbeat': last_heartbeat_time,
            'controller_connected': controller_connected,
            'controller_name': controller_name,
            'timestamp': time.time()
        }
        
        print(f"[Dashboard] Broadcasting update - Commands: {stats.get('total_commands', 0)}, History: {len(history)}")
        socketio.emit('dashboard_update', data, namespace='/')
    except Exception as e:
        print(f"[Warning] Failed to send dashboard update: {e}")
        import traceback
        traceback.print_exc()


@app.route('/api/health')
def health_check():
    """Health check endpoint with controller status"""
    check_controller_status()
    
    return jsonify({
        'status': 'ok',
        'service': 'RobotOS Dashboard',
        'controller': {
            'connected': controller_connected,
            'name': controller_name
        },
        'rpi_connected': rpi_connected
    })


@app.route('/api/controller/status')
def get_controller_status():
    """Get detailed controller connection status"""
    check_controller_status()
    
    return jsonify({
        'connected': controller_connected,
        'name': controller_name,
        'timestamp': time.time()
    })


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
                # Trigger WebSocket update
                send_dashboard_update()
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
    global current_mode, mode_active, mode_thread, mode_stop_event
    
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
        if mode_active and mode_thread and mode_thread.is_alive():
            print(f"[Mode] Stopping current mode: {current_mode}")
            mode_stop_event.set()
            mode_active = False
            time.sleep(1.0)  # Give time to stop
            mode_stop_event.clear()
        
        # Set new mode
        current_mode = new_mode
        print(f"[Mode] Changing to mode: {new_mode}")
        
        # Start the appropriate mode thread
        if new_mode == 'controller':
            if not zmq_socket:
                return jsonify({
                    'status': 'error',
                    'message': 'ZMQ socket not initialized. Cannot start controller mode.'
                }), 503
            
            mode_thread = Thread(target=controller_mode_thread, daemon=True, name="ControllerMode")
            mode_thread.start()
            print("[Mode] Controller mode thread started")
        elif new_mode == 'idle':
            mode_active = False
            print("[Mode] Idle mode - no active control")
        elif new_mode == 'server':
            mode_active = False
            print("[Mode] Server only mode - waiting for external commands")
        elif new_mode == 'sequence':
            mode_active = False
            print("[Mode] Sequence mode - send commands via web interface")
        
        # Broadcast mode change to all connected clients
        try:
            socketio.emit('mode_changed', {'mode': current_mode, 'active': mode_active}, namespace='/')
        except Exception as emit_error:
            print(f"[Warning] Failed to emit mode_changed: {emit_error}")
        
        return jsonify({
            'status': 'success',
            'mode': current_mode,
            'active': mode_active,
            'message': f'Mode changed to {new_mode}'
        })
        
    except Exception as e:
        print(f"[Error] Mode change failed: {e}")
        import traceback
        traceback.print_exc()
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
                # Trigger WebSocket update
                send_dashboard_update()
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
    global background_update_thread
    
    # Record start time for uptime calculation
    app.start_time = time.time()
    
    # Start background update thread
    background_update_thread = Thread(target=periodic_dashboard_update, daemon=True, name="PeriodicUpdater")
    background_update_thread.start()
    
    print(f"\n{'='*60}")
    print(f"🌐 RobotOS Web Dashboard Starting...")
    print(f"{'='*60}")
    print(f"📊 Dashboard URL: http://{host}:{port}")
    print(f"🤖 Monitoring RPi: {RPI_IP}")
    print(f"🔌 Using WebSocket for real-time updates")
    print(f"⏰ Periodic updates every 5 seconds")
    print(f"{'='*60}\n")
    
    # Run Flask app with SocketIO
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


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
    global zmq_socket, background_update_thread
    zmq_socket = sock  # Store socket for control endpoint
    app.start_time = time.time()
    
    # Start background update thread
    background_update_thread = Thread(target=periodic_dashboard_update, daemon=True, name="PeriodicUpdater")
    background_update_thread.start()
    
    dashboard_thread = Thread(
        target=lambda: socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True),
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
    run_dashboard(debug=DEBUG)
