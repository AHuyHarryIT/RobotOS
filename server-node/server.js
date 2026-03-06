/**
 * MQTT Server/Command Handler
 * Listens for commands on robot/command topic and sends responses
 */

const mqtt = require('mqtt');

function runServer() {
  // Connect to MQTT broker (Docker: mqtt-broker:1883, Local: localhost:1883)
  const client = mqtt.connect('mqtt://localhost:1883', {
    clientId: 'server_' + Math.random().toString(16).slice(2, 8),
    clean: true,
    connectTimeout: 4000,
    reconnectPeriod: 1000
  });

  client.on('connect', () => {
    console.log('[Server] Connected to MQTT broker on localhost:1883');

    // Subscribe to command topic
    client.subscribe('robot/command', { qos: 1 }, (err) => {
      if (err) {
        console.error('[Server] Subscribe error:', err);
        process.exit(1);
      }
      console.log('[Server] Listening for commands on robot/command\n');
    });
  });

  // Handle incoming commands
  client.on('message', (topic, message) => {
    if (topic === 'robot/command') {
      const command = message.toString();
      console.log(`[Server] Received command: ${command}`);

      // Process command
      let response;
      if (command === 'ping') {
        response = 'pong';
      } else if (command.startsWith('forward')) {
        response = 'Moving forward';
      } else if (command.startsWith('stop')) {
        response = 'Stopped';
      } else if (command.startsWith('left')) {
        response = 'Turning left';
      } else if (command.startsWith('right')) {
        response = 'Turning right';
      } else {
        response = `Unknown command: ${command}`;
      }

      console.log(`[Server] Sending response: ${response}`);
      client.publish('robot/response', response, { qos: 1 });
    }
  });

  client.on('error', (err) => {
    console.error('[Server] Connection error:', err);
    process.exit(1);
  });

  client.on('close', () => {
    console.log('[Server] Disconnected from broker');
  });

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\nShutting down server...');
    client.end();
    process.exit(0);
  });
}

runServer();
