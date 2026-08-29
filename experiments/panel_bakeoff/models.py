"""Transparent forecasting and donor-imputation estimators for the bake-off."""
from __future__ import annotations

import numpy as np


def seasonal_naive(train: np.ndarray, horizon: int, season_length: int = 7) -> np.ndarray:
    values = np.asarray(train, dtype="float64")
    if len(values) < season_length:
        raise ValueError("Seasonal-naive context is shorter than its season.")
    season = values[-season_length:]
    return np.resize(season, horizon).astype("float64")


def recursive_ar17(train: np.ndarray, horizon: int, ridge_alpha: float = 1e-6) -> np.ndarray:
    """Recursive AR(1,7) with an intercept and deterministic day-of-week terms."""
    y = np.asarray(train, dtype="float64")
    if len(y) < 30:
        raise ValueError("AR(1,7) requires at least 30 observations.")
    t = np.arange(7, len(y))
    dow = t % 7
    x = np.column_stack(
        [y[t - 1], y[t - 7], np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7)]
    )
    x_mean = x.mean(axis=0)
    x_std = x.std(axis=0)
    x_std[x_std == 0] = 1.0
    xz = (x - x_mean) / x_std
    design = np.column_stack([np.ones(len(xz)), xz])
    penalty = np.eye(design.shape[1]) * np.sqrt(ridge_alpha)
    penalty[0, 0] = 0.0
    beta, *_ = np.linalg.lstsq(
        np.vstack([design, penalty]), np.r_[y[t], np.zeros(design.shape[1])], rcond=None
    )
    history = list(y)
    predictions = []
    for lead in range(horizon):
        absolute_t = len(y) + lead
        row = np.array(
            [
                history[-1],
                history[-7],
                np.sin(2 * np.pi * (absolute_t % 7) / 7),
                np.cos(2 * np.pi * (absolute_t % 7) / 7),
            ],
            dtype="float64",
        )
        pred = float(np.dot(np.r_[1.0, (row - x_mean) / x_std], beta))
        pred = max(0.0, pred)
        predictions.append(pred)
        history.append(pred)
    return np.asarray(predictions)


def project_simplex(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype="float64")
    ordered = np.sort(values)[::-1]
    cumulative = np.cumsum(ordered)
    valid = ordered * np.arange(1, len(values) + 1) > cumulative - 1.0
    rho = np.flatnonzero(valid)[-1]
    theta = (cumulative[rho] - 1.0) / (rho + 1.0)
    return np.maximum(values - theta, 0.0)


def synthetic_control(
    target_train: np.ndarray,
    donor_train: np.ndarray,
    donor_future: np.ndarray,
    max_iter: int = 3000,
    tol: float = 1e-9,
) -> tuple[np.ndarray, np.ndarray]:
    """Convex donor weights after unit-specific pre-period mean scaling."""
    y = np.asarray(target_train, dtype="float64")
    x = np.asarray(donor_train, dtype="float64")
    future = np.asarray(donor_future, dtype="float64")
    target_scale = float(np.mean(y))
    donor_scale = np.mean(x, axis=0)
    if target_scale <= 0 or np.any(donor_scale <= 0):
        raise ValueError("Synthetic-control means must be positive.")
    ys = y / target_scale
    xs = x / donor_scale
    fs = future / donor_scale
    gram = np.dot(xs.T, xs)
    cross = np.dot(xs.T, ys)
    lipschitz = 2.0 * float(np.max(np.sum(np.abs(gram), axis=1))) / len(ys)
    weights = np.full(xs.shape[1], 1.0 / xs.shape[1])
    accelerated = weights.copy()
    momentum = 1.0
    for _ in range(max_iter):
        gradient = (2.0 / len(ys)) * (np.dot(gram, accelerated) - cross)
        next_weights = project_simplex(accelerated - gradient / lipschitz)
        if np.linalg.norm(next_weights - weights, ord=1) < tol:
            weights = next_weights
            break
        next_momentum = (1.0 + np.sqrt(1.0 + 4.0 * momentum**2)) / 2.0
        accelerated = next_weights + (momentum - 1.0) / next_momentum * (next_weights - weights)
        weights = next_weights
        momentum = next_momentum
    prediction = np.maximum(0.0, np.dot(fs, weights) * target_scale)
    return prediction, weights


def training_standardization(train: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train = np.asarray(train, dtype="float64")
    means = train.mean(axis=0)
    scales = train.std(axis=0)
    scales[~np.isfinite(scales) | (scales == 0)] = 1.0
    return (train - means) / scales, means, scales


def _right_singular_vectors(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    covariance = np.dot(matrix.T, matrix)
    eigenvalues, vectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    singular_values = np.sqrt(np.maximum(eigenvalues[order], 0.0))
    return vectors[:, order], singular_values


def interactive_fixed_effects(
    train: np.ndarray,
    future: np.ndarray,
    missing_columns: np.ndarray,
    rank: int,
) -> np.ndarray:
    """Hard-rank IFE: learn loadings pre-window, estimate future factors from donors."""
    train_z, means, scales = training_standardization(train)
    loadings, _ = _right_singular_vectors(train_z)
    loadings = loadings[:, :rank]
    future_z = (np.asarray(future, dtype="float64") - means) / scales
    observed = ~np.asarray(missing_columns, dtype=bool)
    factors, *_ = np.linalg.lstsq(loadings[observed], future_z[:, observed].T, rcond=None)
    prediction_z = np.dot(loadings[missing_columns], factors).T
    prediction = prediction_z * scales[missing_columns] + means[missing_columns]
    return np.maximum(0.0, prediction)


def soft_impute(
    matrix: np.ndarray,
    missing_mask: np.ndarray,
    lambda_fraction: float,
    max_iter: int = 100,
    tol: float = 1e-5,
) -> tuple[np.ndarray, int, int]:
    """Exact singular-value soft thresholding using an N x N eigendecomposition."""
    observed_matrix = np.asarray(matrix, dtype="float64")
    missing = np.asarray(missing_mask, dtype=bool)
    estimate = np.zeros_like(observed_matrix)
    initialized = np.where(missing, 0.0, observed_matrix)
    _, initial_singular = _right_singular_vectors(initialized)
    penalty = float(lambda_fraction) * float(initial_singular[0])
    retained_rank = 0
    for iteration in range(1, max_iter + 1):
        filled = np.where(missing, estimate, observed_matrix)
        vectors, singular = _right_singular_vectors(filled)
        keep = singular > penalty
        retained_rank = int(keep.sum())
        if retained_rank == 0:
            updated = np.zeros_like(filled)
        else:
            right = vectors[:, keep]
            ratios = 1.0 - penalty / singular[keep]
            updated = np.dot(np.dot(filled, right) * ratios, right.T)
        old_missing = estimate[missing]
        new_missing = updated[missing]
        denominator = max(float(np.linalg.norm(old_missing)), 1.0)
        estimate = updated
        if float(np.linalg.norm(new_missing - old_missing)) / denominator < tol:
            break
    return estimate, iteration, retained_rank


def nuclear_norm_completion(
    train: np.ndarray,
    future: np.ndarray,
    missing_columns: np.ndarray,
    lambda_fraction: float,
) -> tuple[np.ndarray, int, int]:
    """SoftImpute a complete future block for a spatially held-out unit group."""
    train_z, means, scales = training_standardization(train)
    future_z = (np.asarray(future, dtype="float64") - means) / scales
    stacked = np.vstack([train_z, future_z])
    mask = np.zeros_like(stacked, dtype=bool)
    mask[-len(future_z):, missing_columns] = True
    completed, iterations, rank = soft_impute(stacked, mask, lambda_fraction)
    prediction_z = completed[-len(future_z):, missing_columns]
    prediction = prediction_z * scales[missing_columns] + means[missing_columns]
    return np.maximum(0.0, prediction), iterations, rank
