# Web Dashboard Quick Guide

## 🌐 Real-time Command Monitoring Web Interface

The dashboard provides a visual interface for monitoring RobotOS activity.

### Starting the Dashboard

#### Method 1: From Client Menu
```bash
cd server/
python3 main.py
# Select option 4 (Web Dashboard)
```

#### Method 2: Run Standalone
```bash
cd server/
python3 web_dashboard.py
```

Dashboard will run at: `http://localhost:5000`

### Access from Other Devices

To view the dashboard from a phone or another computer on the same network:

```
http://<miniPC-IP>:5000
```

**Example:**
- If miniPC has IP `192.168.1.100`
- Access: `http://192.168.1.100:5000`

### Dashboard Features

#### 📊 Real-time Statistics
- **Total commands** processed
- **Breakdown by source:**
  - 🎥 Jetson Vision (red)
  - 🎮 Xbox Controller (blue)
  - ⌨️ Manual Input (green)
  - 📝 Sequence Mode (yellow)

#### 📜 Command History
- Displays last 20 commands
- Execution timestamp
- Color-coded command sources
- Auto-scroll on new commands

#### 💓 System Status
- **Green indicator**: RPi connected
- **Red indicator**: RPi disconnected
- **Uptime**: System running time
- **Last Update**: Last refresh timestamp

#### 🔄 Auto-refresh
Dashboard automatically refreshes every **1 second** to display the latest data.

### Test Dashboard (Without RPi)

To test the dashboard without needing an RPi connection:

```bash
cd server/

# Step 1: Generate test data
python3 test_dashboard.py

# Step 2: Start the dashboard
python3 web_dashboard.py

# Step 3: Open browser
# http://localhost:5000
```

The `test_dashboard.py` script will create sample commands so you can see the dashboard in action.

### API Endpoints

The dashboard provides the following API endpoints:

#### `/api/stats`
Returns statistics and command history in JSON format:
```json
{
  "stats": {
    "total_commands": 42,
    "by_source": {
      "JETSON": 10,
      "CONTROLLER": 20,
      "MANUAL": 8,
      "SEQUENCE": 4
    },
    "errors": 0,
    "last_command": "forward 2"
  },
  "history": [
    {
      "command": "forward 2",
      "source": "CONTROLLER",
      "processed": "forward 2",
      "timestamp": 1702800123.45
    }
  ],
  "uptime": "2h 15m 30s",
  "rpi_connected": true,
  "timestamp": 1702800150.12
}
```

#### `/api/health`
Health check endpoint:
```json
{
  "status": "ok",
  "service": "RobotOS Dashboard"
}
```

### Using in Production

#### Running Dashboard in Background

The dashboard can run alongside other modes (Controller, Sequence):

```python
from web_dashboard import run_dashboard_background

# Start dashboard in background thread
dashboard_thread = run_dashboard_background(host='0.0.0.0', port=5000)

# Continue with other operations
# Dashboard will keep running in background
```

#### Port Configuration

By default, the dashboard runs on port **5000**. To change it:

```python
from web_dashboard import run_dashboard

run_dashboard(host='0.0.0.0', port=8080)
```

### Troubleshooting

#### Dashboard not displaying data
1. Check if command aggregator has been initialized
2. Ensure client is running and receiving commands
3. Open Developer Console in browser to see errors

#### Cannot access from other devices
1. Check if firewall is blocking port 5000
2. Ensure dashboard is bound to correct interface (`0.0.0.0`)
3. Verify miniPC IP address is correct

#### Error "Module not found: flask"
```bash
pip install flask
# or
pip install -r requirements.txt
```

### Security Notes

⚠️ **Warning:** The dashboard currently has no authentication.

If deploying on a public network, you should:
1. Add HTTP authentication
2. Use HTTPS (reverse proxy with nginx/caddy)
3. Limit access with firewall rules

### Advanced Usage

#### Customize Refresh Interval

Edit in `templates/index.html`:

```javascript
// Change from 1000ms (1s) to 500ms (0.5s)
const UPDATE_INTERVAL = 500;
```

#### Add Audio Notification

Uncomment code in `index.html`:

```javascript
if (currentCount > lastCommandCount && lastCommandCount > 0) {
    // Add notification sound here
    new Audio('notification.mp3').play();
}
```

---

## Screenshots

### Main Dashboard
![Dashboard Overview](docs/images/dashboard-overview.png)

### Live Statistics
![Statistics](docs/images/dashboard-stats.png)

### Command History
![History](docs/images/dashboard-history.png)

---

**Enjoy monitoring RobotOS with a beautiful interface! 🚀**
