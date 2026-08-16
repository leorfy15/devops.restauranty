// ℹ️ Gets access to environment variables/settings
require("dotenv").config();

// ℹ️ Connects to the database
require("./db");

// Handles http requests
const express = require("express");
const cors = require("cors");
const mongoose = require("mongoose");
const client = require("prom-client");
const { httpMetricsMiddleware } = require("./metrics.cjs");

const app = express();

app.use(
  cors({
    origin: "*",
  })
);

app.use(httpMetricsMiddleware);

// Runs middleware/config
require("./config")(app);

require("./metrics.cjs");
client.collectDefaultMetrics();


// Basic service check
app.get("/api/items", (req, res) => {
  res.json("Items Server UP!");
});


// Application routes
const itemsRoutes = require("./routes/items.routes");
app.use("/api/items/items", itemsRoutes);

const DietaryRoutes = require("./routes/dietary.routes");
app.use("/api/items/dietary", DietaryRoutes);

const OrdersRoutes = require("./routes/orders.routes");
app.use("/api/items/orders", OrdersRoutes);


// Health endpoint
app.get("/health", (req, res) => {
  const mongoConnected = mongoose.connection.readyState === 1;

  if (mongoConnected) {
    return res.status(200).json({
      status: "healthy",
      service: "items",
      mongodb: "connected",
    });
  }

  return res.status(503).json({
    status: "unhealthy",
    service: "items",
    mongodb: "disconnected",
  });
});


// Prometheus metrics endpoint
app.get("/metrics", async (req, res) => {
  try {
    res.set("Content-Type", client.register.contentType);

    const metrics = await client.register.metrics();

    res.end(metrics);
  } catch (ex) {
    res.status(500).end(ex);
  }
});


// Handle routes that don't exist and application errors
require("./error-handling")(app);

module.exports = app;