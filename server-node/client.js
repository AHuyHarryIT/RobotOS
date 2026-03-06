/**
 * MQTT Client
 * Sends and receives messages using MQTT
 */

const mqtt = require('mqtt');

function runClient() {
  // Connect to MQTT broker (Docker: mqtt-broker:1883, Local: localhost:1883)
  const client = mqtt.connect('mqtt://localhost:1883', {
    clientId: 'client_' + Math.random().toString(16).slice(2, 8),
    clean: true,
    connectTimeout: 4000,
    reconnectPeriod: 1000
  });

  client.on('connect', () => {
    console.log('[Client] Connected to MQTT broker on localhost:1883\n');

    // Subscribe to response topic
    client.subscribe('robot/response', { qos: 1 }, (err) => {
      if (err) console.error('[Client] Subscribe error:', err);
    });

    // Send test commands
    const commands = ['ping', 'forward', 'forward 2', 'stop', 'invalid'];
    let index = 0;

    const interval = setInterval(() => {
      if (index >= commands.length) {
        clearInterval(interval);
        console.log('\n[Client] Finished sending commands');
        setTimeout(() => client.end(), 500);
        return;
      }

      const cmd = commands[index];
      console.log(`[Client] Publishing command: ${cmd}`);
      client.publish('robot/command', cmd, { qos: 1 });
      index++;
    }, 800);
  });

  // Handle incoming messages
  client.on('message', (topic, message) => {
    if (topic === 'robot/response') {
      console.log(`[Client] Response: ${message.toString()}\n`);
    }
  });

  client.on('error', (err) => {
    console.error('[Client] Connection error:', err);
    process.exit(1);
  });

  client.on('close', () => {
    console.log('[Client] Disconnected from broker');
  });

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\nShutting down client...');
    client.end();
    process.exit(0);
  });
}

runClient();
