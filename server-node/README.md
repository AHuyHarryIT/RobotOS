# MQTT Node.js System (Docker-based)

A simple MQTT distributed system using Node.js with Docker-based Mosquitto broker.

## Prerequisites

- Docker & Docker Compose (or `docker compose`)
- Node.js 14+ and npm

## Quick Start

```bash
# 1. Install npm dependencies
npm install

# 2. Start MQTT broker in Docker (Mosquitto)
docker compose up -d

# 3. Verify broker is running
docker ps | grep mqtt
```

## Running Examples

### Server/Client Pattern (Request-Response via MQTT)

**Terminal 1 - Start server:**
```bash
npm run server
```

**Terminal 2 - Run client:**
```bash
npm run client
```

### Publisher/Subscriber Pattern (Pub-Sub via MQTT)

**Terminal 1 - Start publisher:**
```bash
npm run publisher
```

**Terminal 2 - Start subscriber:**
```bash
npm run subscriber
```

You can run multiple subscribers simultaneously - all will receive published messages.

## Architecture

### MQTT Broker (Docker)
- **Container**: `eclipse-mosquitto:latest`
- **Port**: 1883 (MQTT), 9001 (WebSocket)
- **Config File**: `mosquitto.conf`
- **Data Volume**: `mosquitto_data` (persistence)
- **Logs Volume**: `mosquitto_logs`
- **Anonymous Access**: Enabled by default

### Server/Client Pattern
- **Server** (`server.js`): Listens on `robot/command` topic, publishes responses to `robot/response`
- **Client** (`client.js`): Publishes commands, subscribes to response topic
- Request-response style communication

### Publisher/Subscriber Pattern
- **Publisher** (`publisher.js`): Publishes status messages to `motion`, `status`, `error` topics
- **Subscriber** (`subscriber.js`): Subscribes to all topics and receives updates
- Asynchronous, fire-and-forget messaging

## Available Commands (Server)

- `ping` → Responds with `pong`
- `forward` or `forward N` → Responds with `Moving forward`
- `stop` → Responds with `Stopped`
- `left` → Responds with `Turning left`
- `right` → Responds with `Turning right`
- Any other command → Responds with `Unknown command: ...`

## MQTT Topics

**Server/Client Pattern**:
- `robot/command` - Client publishes commands
- `robot/response` - Server publishes responses

**Publisher/Subscriber Pattern**:
- `motion` - Motion events (forward, backward, left, right, stop)
- `status` - System status (ready, busy, idle, calibrating)
- `error` - Error events (motor_error, sensor_error, connection_error)

## Docker Commands

```bash
# Start broker
docker compose up -d

# Stop broker
docker compose down

# View broker logs
docker logs mqtt-broker

# Follow broker logs in real-time
docker logs -f mqtt-broker

# Remove volumes (data loss!)
docker compose down -v
```

## Network Configuration

By default, clients connect to `localhost:1883`. To use across network:

**Docker Compose** - Expose all interfaces:
```yaml
mqtt-broker:
  ports:
    - "0.0.0.0:1883:1883"  # Listen on all interfaces
```

**Node.js Code** - Use broker IP:
```javascript
mqtt.connect('mqtt://192.168.x.x:1883')
```

## Mosquitto Configuration (`mosquitto.conf`)

Key settings:
- `listener 1883` - MQTT port
- `listener 9001` - WebSocket port
- `allow_anonymous true` - Allow connections without credentials
- `max_connections -1` - Max concurrent clients (-1 = unlimited)
- `max_queued_messages 100` - Buffer size per client
- `persistence true` - Save messages to disk

For production, also set:
- `allow_anonymous false`
- Add username/password in separate file
- Enable SSL/TLS on port 8883
- Configure ACLs (Access Control Lists)

## Development Workflow

1. **Start broker once**: `docker compose up -d`
2. **Terminal 1**: `npm run server` (listen for commands)
3. **Terminal 2**: `npm run client` (send test commands)
4. **Make code changes** - Restart services as needed
5. **Check logs**: `docker logs -f mqtt-broker`
6. **Stop broker**: `docker compose down`

## Troubleshooting

**Connection refused**
```bash
# Check if broker is running
docker ps | grep mqtt

# Check port availability
netstat -tlnp | grep 1883

# View broker logs
docker logs mqtt-broker
```

**Messages not received**
- Subscriber must connect BEFORE messages are published
- Topic names are case-sensitive
- Verify QoS settings (0, 1, or 2)
- Check `allow_anonymous` setting

**Broker won't start**
- Check `mosquitto.conf` syntax (no `loglevel` in v2.1+)
- Remove Docker container: `docker compose down -v`
- Restart: `docker compose up -d`

## Dependencies

- `mqtt@^5.0.0` - MQTT client library for Node.js
- `docker` & `docker-compose` - Container orchestration

## File Structure

```
server-node/
├── docker-compose.yml    # Docker configuration for Mosquitto
├── mosquitto.conf        # Mosquitto broker configuration
├── package.json          # Node.js project manifest
├── README.md             # This file
├── server.js             # Server listening for commands
├── client.js             # Client sending commands
├── publisher.js          # Publisher for status updates
└── subscriber.js         # Subscriber for status updates
```

## Performance Tips

- Use QoS 0 for high-frequency telemetry (no guarantee)
- Use QoS 1 for important commands (exactly once)
- Set appropriate `max_queued_messages` for your workload
- Monitor CPU/memory with `docker stats mqtt-broker`
- Use topic filtering on subscriber for relevant messages

## Production Deployment

For a production environment:

1. **Security**
   - Disable `allow_anonymous`
   - Use username/password authentication
   - Enable SSL/TLS
   - Set firewall rules

2. **Reliability**
   - Enable persistence
   - Set message retention policies
   - Monitor broker health
   - Use Docker restart policy: `restart: unless-stopped`

3. **Scalability**
   - Use broker clustering for high load
   - Distribute subscribers across machines
   - Monitor resource usage

## License

MIT

