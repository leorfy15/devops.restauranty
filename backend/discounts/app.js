// ℹ️ Gets access to environment variables/settings
// https://www.npmjs.com/package/dotenv
require("dotenv").config();

// ℹ️ Connects to the database
require("./db");

// Handles http requests (express is node js framework)
// https://www.npmjs.com/package/express
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

// ℹ️ This function is getting exported from the config folder.
// It runs most pieces of middleware
require("./config")(app);

require("./metrics.cjs");
client.collectDefaultMetrics();

// Basic Discounts service check
app.get("/api/discounts", (req, res) => {
  res.json("Discounts Server UP!");
});

// Coupon routes
const CouponRoutes = require("./routes/coupons.routes");
app.use("/api/discounts/coupons", CouponRoutes);

// Campaign routes
const CampaignRoutes = require("./routes/campaigns.routes");
app.use("/api/discounts/campaign", CampaignRoutes);

// Health endpoint
// Kubernetes readiness probe will use this endpoint.
app.get("/health", (req, res) => {
  const mongoConnected = mongoose.connection.readyState === 1;

  if (mongoConnected) {
    return res.status(200).json({
      status: "healthy",
      service: "discounts",
      mongodb: "connected",
    });
  }

  return res.status(503).json({
    status: "unhealthy",
    service: "discounts",
    mongodb: "disconnected",
  });
});

// Expose /metrics endpoint for Prometheus
app.get("/metrics", async (req, res) => {
  try {
    res.set("Content-Type", client.register.contentType);

    const metrics = await client.register.metrics();

    res.end(metrics);
  } catch (ex) {
    res.status(500).end(ex);
  }
});

// ❗ Handle routes that don't exist and application errors
require("./error-handling")(app);

module.exports = app;