/**
 * MQTT Broker
 * Runs a local MQTT broker using Aedes
 */

const aedes = require('aedes');
const net = require('net');

// Create broker
const broker = new aedes();

// Create TCP server for MQTT
const server = net.createServer(broker.handle.bind(broker));
const PORT = 1883;

server.listen(PORT, () => {
  console.log(`MQTT Broker listening on port ${PORT}`);
});

// Listen for client connections
broker.on('client', (client) => {
  console.log(`[Broker] Client connected: ${client.id}`);
});

// Listen for client disconnections
broker.on('clientDisconnect', (client) => {
  console.log(`[Broker] Client disconnected: ${client.id}`);
});

// Listen for published messages
broker.on('publish', async (packet, client) => {
  if (client) {
    console.log(`[Broker] Message from ${client.id} on topic "${packet.topic}": ${packet.payload.toString()}`);
  }
});

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down broker...');
  server.close(() => {
    broker.close();
    process.exit(0);
  });
});
