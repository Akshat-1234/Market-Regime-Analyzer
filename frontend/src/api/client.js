import { API } from "../config.js";

async function request(path, options) {
  const response = await fetch(`${API}${path}`, options);

  let data = null;

  try {
    data = await response.json();
  } catch {
    // Response was not JSON.
  }

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        data?.message ??
        `Request failed (${response.status})`
    );
  }

  return data;
}

export const getHealth = () => request("/api/health");

export const getStrategies = () => request("/api/strategies");

export const getDataInfo = () => request("/api/data-info");

// Run a baseline strategy.
export const postBacktest = (payload) =>
  request("/api/backtest", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

// Run HMM Adaptive.
export const postAdaptiveBacktest = (payload) =>
  request("/api/adaptive-backtest", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

// Select the endpoint based on the strategy.
export const runBacktest = (strategy, payload) => {
  if (strategy === "hmm_adaptive") {
    return postAdaptiveBacktest(payload);
  }

  return postBacktest(payload);
};