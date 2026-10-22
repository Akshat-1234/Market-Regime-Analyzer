import { API } from "../config.js";

async function request(path, options) {
  const response = await fetch(`${API}${path}`, options);
  let data = null;
  try {
    data = await response.json();
  } catch {
    /* non-JSON body */
  }
  if (!response.ok) {
    throw new Error(
      data?.detail ?? data?.message ?? `Request failed (${response.status})`
    );
  }
  return data;
}

export const getHealth = () => request("/api/health");
export const getStrategies = () => request("/api/strategies");
export const getDataInfo = () => request("/api/data-info");

export const postBacktest = (payload) =>
  request("/api/backtest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
