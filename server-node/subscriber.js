/**
 * MQTT Subscriber
 * Subscribes to topics and receives messages from the MQTT broker
 */

const mqtt = require('mqtt');

function runSubscriber() {
  // Connect to MQTT broker (Docker: mqtt-broker:1883, Local: localhost:1883)
  const client = mqtt.connect('mqtt://localhost:1883', {
    clientId: 'subscriber_' + Math.random().toString(16).slice(2, 8),
    clean: true,
    connectTimeout: 4000,
    reconnectPeriod: 1000
  });

  client.on('connect', () => {
    console.log('[Subscriber] Connected to MQTT broker on localhost:1883');

    // Subscribe to topics
    const topics = ['motion', 'status', 'error'];
    client.subscribe(topics, { qos: 1 }, (err) => {
      if (err) {
        console.error('[Subscriber] Subscribe error:', err);
        process.exit(1);
      }
      console.log(`[Subscriber] Subscribed to: ${topics.join(', ')}`);
    });
  });

  // Handle incoming messages
  client.on('message', (topic, message) => {
    console.log(`[Subscriber] Received on "${topic}": ${message.toString()}`);
  });

  client.on('error', (err) => {
    console.error('[Subscriber] Connection error:', err);
    process.exit(1);
  });

  client.on('close', () => {
    console.log('[Subscriber] Disconnected from broker');
  });

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\nShutting down subscriber...');
    client.end();
    process.exit(0);
  });
}

runSubscriber();
