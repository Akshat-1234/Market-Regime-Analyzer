"""Train-only preprocessing and a causal log-space Gaussian-HMM filter.

Only the forward recursion is used for decisions; hmmlearn's predict/predict_proba
smooth or decode using later observations and must not be used as live signals.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


def _safe_log_probability(p: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore"):
        return np.log(p)


def forward_filter(model: GaussianHMM, observations: np.ndarray,
                   previous_log_alpha: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Filter an ordered block; previous_log_alpha is the PREVIOUS observation.

    hmmlearn has no public emission-log-density API. Its private
    _compute_log_likelihood is used here; the hmmlearn version is constrained.
    """
    x = np.asarray(observations, dtype=float)
    if x.ndim != 2 or len(x) == 0 or not np.isfinite(x).all():
        raise ValueError("Filter observations must be a nonempty finite 2D array")
    log_emit = model._compute_log_likelihood(x)
    k = model.n_components
    log_trans = _safe_log_probability(np.asarray(model.transmat_, dtype=float))
    if previous_log_alpha is None:
        alpha = _safe_log_probability(np.asarray(model.startprob_, dtype=float)) + log_emit[0]
    else:
        previous = np.asarray(previous_log_alpha, dtype=float)
        if previous.shape != (k,) or not np.isfinite(logsumexp(previous)):
            raise ValueError("previous_log_alpha is invalid")
        alpha = logsumexp(previous[:, None] + log_trans, axis=0) + log_emit[0]
    z = logsumexp(alpha)
    if not np.isfinite(z):
        raise ValueError("HMM filtering produced no finite posterior")
    alpha -= z
    probs = np.empty((len(x), k), dtype=float)
    probs[0] = np.exp(alpha)
    for i in range(1, len(x)):
        alpha = logsumexp(alpha[:, None] + log_trans, axis=0) + log_emit[i]
        z = logsumexp(alpha)
        if not np.isfinite(z):
            raise ValueError("HMM filtering produced no finite posterior")
        alpha -= z
        probs[i] = np.exp(alpha)
    return probs, alpha


@dataclass
class FittedRegime:
    model: GaussianHMM
    scaler: StandardScaler
    pca: PCA | None
    last_train_alpha: np.ndarray
    order: np.ndarray
    state_vols: np.ndarray
    state_means: np.ndarray
    exposures: np.ndarray
    occupancy: np.ndarray
    diagnostics: dict[str, Any]

    def filter_new(self, raw: np.ndarray) -> np.ndarray:
        transformed = self.scaler.transform(np.asarray(raw, dtype=float))
        if self.pca is not None:
            transformed = self.pca.transform(transformed)
        p, _ = forward_filter(self.model, transformed, self.last_train_alpha)
        return p[:, self.order]

    @property
    def sorted_transition(self) -> np.ndarray:
        return self.model.transmat_[np.ix_(self.order, self.order)]


def fit_regime(train_x: np.ndarray, train_returns: np.ndarray, spec: dict,
               config: dict, annualization: int = 252) -> FittedRegime:
    """Fit one specification using only a complete chronological train window.

    State exposure is calibrated with P(S_t | X_<=t) and return t+1, retaining
    only outcomes whose dates are inside this training window.
    """
    x = np.asarray(train_x, dtype=float)
    r = np.asarray(train_returns, dtype=float)
    h = config["hmm"]
    if x.ndim != 2 or len(x) != len(r) or len(x) < 30:
        raise ValueError("Training features and returns must be aligned and contain at least 30 rows")
    if not np.isfinite(x).all() or not np.isfinite(r).all():
        raise ValueError("Training inputs must be finite")
    if (np.std(x, axis=0) < 1e-12).any():
        raise ValueError(f"{spec['name']}: a training feature is constant")
    scaler = StandardScaler()
    scaled = scaler.fit_transform(x)
    pca = None
    if spec.get("pca_components") is not None:
        pca = PCA(n_components=spec["pca_components"], svd_solver="full")
        scaled = pca.fit_transform(scaled)
    candidates: list[tuple[float, GaussianHMM, np.ndarray, np.ndarray, np.ndarray, int, int, float]] = []
    failures = []
    for seed in h["seeds"]:
        try:
            m = GaussianHMM(n_components=spec["n_states"], covariance_type=h["covariance_type"],
                            n_iter=h["n_iter"], tol=h["tol"], min_covar=h["min_covar"],
                            random_state=seed, implementation="log")
            # BLAS oversubscription can make small HMM fits orders of magnitude slower.
            with threadpool_limits(limits=1):
                m.fit(scaled)
                score = float(m.score(scaled))
            hist = np.asarray(m.monitor_.history, dtype=float)
            change = hist[-1] - hist[-2] if len(hist) >= 2 else np.inf
            # hmmlearn calls hitting max_iter "converged"; require actual tolerance.
            converged = len(hist) >= 2 and -1e-6 <= change < h["tol"]
            if not converged:
                failures.append(f"seed {seed}: did not meet convergence tolerance (last change={change:.4g})")
                continue
            if (not np.isfinite(score) or not np.isfinite(m.transmat_).all()
                or (m.transmat_ < 0).any() or not np.allclose(m.transmat_.sum(axis=1), 1)
                or not np.isfinite(m.startprob_).all() or (m.startprob_ < 0).any()
                or not np.isclose(m.startprob_.sum(), 1)):
                failures.append(f"seed {seed}: invalid likelihood/transition matrix")
                continue
            eigenvalues = np.linalg.eigvalsh(m.covars_)
            if not np.isfinite(eigenvalues).all() or (eigenvalues <= 0).any():
                failures.append(f"seed {seed}: invalid covariance")
                continue
            probabilities, final_alpha = forward_filter(m, scaled)
            labels = probabilities.argmax(axis=1)
            occupancy = np.bincount(labels, minlength=spec["n_states"]) / len(labels)
            if (occupancy < h["min_state_fraction"]).any():
                failures.append(f"seed {seed}: a state has too little train occupancy")
                continue
            candidates.append((score, m, probabilities, final_alpha, occupancy, seed, int(m.monitor_.iter), float(change)))
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
            failures.append(f"seed {seed}: {exc}")
    if not candidates:
        raise RuntimeError(f"All fits rejected for {spec['name']}: {'; '.join(failures)}")
    score, model, probs, last_alpha, occupancy, seed, iterations, last_change = max(candidates, key=lambda z: z[0])
    means, vols = [], []
    for state in range(spec["n_states"]):
        w = probs[:-1, state]
        y = r[1:]  # train t+1 outcomes, excludes the first OOS outcome
        if w.sum() <= 1e-12:
            raise RuntimeError(f"{spec['name']}: state has no usable calibration weight")
        mean = float(np.dot(w, y) / w.sum())
        variance = float(np.dot(w, (y - mean) ** 2) / w.sum())
        means.append(mean)
        vols.append(np.sqrt(max(0.0, variance) * annualization))
    order = np.argsort(vols, kind="stable")
    state_vols = np.asarray(vols)[order]
    state_means = np.asarray(means)[order]
    exposure = np.clip(h["target_volatility"] / np.maximum(state_vols, h["volatility_floor"]), 0, 1)
    diagnostics = {"seed": seed, "iterations": iterations, "log_likelihood": score,
                   "last_likelihood_change": last_change, "rejected_seeds": "; ".join(failures),
                   "pca_explained_variance": float(pca.explained_variance_ratio_.sum()) if pca is not None else None}
    return FittedRegime(model, scaler, pca, last_alpha, order, state_vols,
                        state_means, exposure, occupancy[order], diagnostics)
