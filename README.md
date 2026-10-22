# Market Regime-Based Strategy Analyzer

## Problem Statement

Markets exhibit different behavioural conditions over time, and trading strategies may perform differently under these conditions.

This project aims to develop an **HMM-based adaptive trading strategy** for the NIFTY 50. Historical market data will be used to infer latent market regimes from observable characteristics such as returns, volatility, and trend. The performance of different trading strategies will then be analyzed across the identified regimes.

Finally, we will investigate whether dynamically selecting a strategy according to the inferred market regime can improve **risk-adjusted out-of-sample performance** compared with fixed strategies and a buy-and-hold benchmark.

---

## Research Hypotheses

### H1 — Market Regime Hypothesis

> **NIFTY 50 exhibits persistent and distinguishable market regimes that can be inferred from observable market characteristics using an unsupervised Hidden Markov Model (HMM).**

We will evaluate whether the inferred states exhibit meaningful differences in:

- Returns
- Volatility
- Trend
- Regime duration
- Transition probabilities
- Frequency of occurrence

The objective is to determine whether the HMM states can be given economically meaningful interpretations.

---

### H2 — Regime-Dependent Strategy Hypothesis

> **Different trading strategies exhibit materially different risk-adjusted performance across the market regimes identified by the HMM.**

Strategies such as:

- Momentum / Trend Following
- Mean Reversion
- Buy and Hold

will be evaluated separately within each identified market regime.

The objective is to determine whether the effectiveness of a strategy depends on the prevailing market regime.

---

### H3 — Adaptive Strategy Hypothesis

> **An HMM-based adaptive strategy that dynamically selects a trading strategy according to the inferred market regime can achieve better risk-adjusted performance than using a single fixed strategy across all market conditions.**

Based on the relationship observed between regimes and strategy performance, an adaptive strategy will select among the available strategies according to the inferred regime.

For example:

```text
Market Regime
      ↓
 ┌────┼────┐
 ↓    ↓    ↓
 R1   R2   R3
 ↓    ↓    ↓
 M    MR   Cash