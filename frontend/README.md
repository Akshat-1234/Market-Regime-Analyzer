# QuantLab Frontend

React + Vite frontend for the QuantLab backtesting API.

## Run

```bash
npm install
npm run dev
```

Open http://localhost:5173. Start your FastAPI backend on port 8000 first
(or copy `.env.example` to `.env` and change `VITE_API_URL`).

## Structure

```
src/
  main.jsx                 entry point (Router + provider)
  App.jsx                  layout shell + routes
  config.js                API base URL, defaults
  api/client.js            all fetch calls
  context/BacktestContext  shared state (API status, data info, last result)
  utils/                   formatters + response normalisers
  pages/                   StrategyLab, Performance, DataExplorer, NotFound
  components/
    layout/                Sidebar, Topbar, Footer
    common/                PageHeading, Panel
    backtest/              BacktestForm, MetricsGrid, EquityChart, DataStrip
  styles/                  global, layout, components CSS
```
