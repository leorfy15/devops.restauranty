const mongoose = require("mongoose");
const client = require("prom-client");

const mongoConnectionGauge = new client.Gauge({
  name: "mongo_connection_status",
  help: "Indicates MongoDB connection status: 1 for connected, 0 for disconnected"
});

const MONGO_URI =
  process.env.MONGODB_URI ||
  "mongodb://127.0.0.1:27017/Restauranty";

const RETRY_DELAY = 5000;

async function connectToMongo() {
  try {
    console.log(`Connecting to MongoDB: ${MONGO_URI}`);

    const connection = await mongoose.connect(MONGO_URI);

    const dbName = connection.connections[0].name;

    console.log(`Connected to Mongo! Database name: "${dbName}"`);

    mongoConnectionGauge.set(1);

  } catch (err) {
    console.error("Error connecting to MongoDB:", err.message);

    mongoConnectionGauge.set(0);

    console.log("Retrying MongoDB connection in 5 seconds...");

    setTimeout(connectToMongo, RETRY_DELAY);
  }
}

mongoose.connection.on("disconnected", () => {
  console.log("MongoDB disconnected");
  mongoConnectionGauge.set(0);

  setTimeout(connectToMongo, RETRY_DELAY);
});

mongoose.connection.on("reconnected", () => {
  console.log("MongoDB reconnected");
  mongoConnectionGauge.set(1);
});

connectToMongo();