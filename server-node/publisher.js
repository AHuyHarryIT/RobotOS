/**
 * MQTT Publisher
 * Publishes messages to MQTT broker
 */

const mqtt = require('mqtt');

function runPublisher() {
  // Connect to MQTT broker (Docker: mqtt-broker:1883, Local: localhost:1883)
  const client = mqtt.connect('mqtt://localhost:1883', {
    clientId: 'publisher_' + Math.random().toString(16).slice(2, 8),
    clean: true,
    connectTimeout: 4000,
    reconnectPeriod: 1000
  });

  const topics = ['motion', 'status', 'error'];
  const messages = {
    motion: ['forward', 'backward', 'left', 'right', 'stop'],
    status: ['ready', 'busy', 'idle', 'calibrating'],
    error: ['motor_error', 'sensor_error', 'connection_error']
  };

  client.on('connect', () => {
    console.log('[Publisher] Connected to MQTT broker on localhost:1883');
    let messageCount = 0;

    const publishInterval = setInterval(() => {
      const topic = topics[Math.floor(Math.random() * topics.length)];
      const msg = messages[topic][Math.floor(Math.random() * messages[topic].length)];
      const timestamp = new Date().toISOString();
      const fullMessage = `${msg} [${timestamp}]`;

      client.publish(topic, fullMessage, { qos: 1 }, (err) => {
        if (err) {
          console.error(`[Publisher] Error publishing to ${topic}:`, err);
        } else {
          console.log(`[Publisher] Published to ${topic}: ${fullMessage}`);
        }
      });

      messageCount++;
      if (messageCount >= 10) {
        clearInterval(publishInterval);
        console.log('[Publisher] Finished publishing 10 messages');
        setTimeout(() => client.end(), 500);
      }
    }, 1000);
  });

  client.on('error', (err) => {
    console.error('[Publisher] Connection error:', err);
    process.exit(1);
  });

  client.on('close', () => {
    console.log('[Publisher] Disconnected from broker');
  });
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down publisher...');
  process.exit(0);
});

runPublisher();
