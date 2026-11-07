"""Fixed models, expanding-session validation, ablation and block-bootstrap inference."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from crowd_signal.analytics import NEWS_FEATURES, PRICE_FEATURES, SOCIAL_FEATURES

FEATURE_SETS = {
    "price_only": PRICE_FEATURES,
    "price_social": PRICE_FEATURES + SOCIAL_FEATURES,
    "price_news": PRICE_FEATURES + NEWS_FEATURES,
    "all": PRICE_FEATURES + SOCIAL_FEATURES + NEWS_FEATURES,
}


def design_matrix(frame: pd.DataFrame, features: list[str], universe: list[str]) -> np.ndarray:
    indicators = np.column_stack(
        [(frame.ticker == ticker).astype(float).to_numpy() for ticker in universe]
    )
    return np.column_stack([frame[features].to_numpy(dtype=float), indicators])


def estimator(kind: str):
    if kind == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    if kind == "boost":
        return GradientBoostingRegressor(
            n_estimators=35,
            max_depth=2,
            learning_rate=0.04,
            min_samples_leaf=10,
            loss="huber",
            random_state=42,
        )
    raise ValueError(f"Unknown model {kind}")


def causal_training_rows(frame: pd.DataFrame, test_session: str) -> pd.DataFrame:
    return frame[
        (frame.session < test_session)
        & frame.target_log_return.notna()
        & (frame.target_session <= test_session)
    ]


def block_indices(count: int, repetitions: int, seed: int = 42, block: int = 5) -> np.ndarray:
    random = np.random.default_rng(seed)
    starts = random.integers(0, count, size=(repetitions, int(np.ceil(count / block))))
    return ((starts[:, :, None] + np.arange(block)) % count).reshape(repetitions, -1)[:, :count]


def metrics(rows: pd.DataFrame, baseline: pd.DataFrame, repetitions: int) -> dict:
    merged = rows.merge(
        baseline[["session", "ticker", "predicted_price"]].rename(
            columns={"predicted_price": "baseline_price"}
        ),
        on=["session", "ticker"],
        validate="one_to_one",
    )
    if merged.empty:
        raise ValueError("No matched out-of-sample predictions")
    error = (merged.predicted_price - merged.actual_price).to_numpy()
    absolute = np.abs(error)
    base_absolute = np.abs((merged.baseline_price - merged.actual_price).to_numpy())
    actual_return = np.sign(np.log(merged.actual_price / merged.close))
    predicted_return = np.sign(np.log(merged.predicted_price / merged.close))
    direction = (actual_return == predicted_return).to_numpy(dtype=float)
    wins = (absolute < base_absolute).astype(float) + 0.5 * (absolute == base_absolute)
    values = (
        pd.DataFrame(
            {
                "session": merged.session,
                "mae": absolute,
                "mse": error**2,
                "mape": absolute / merged.actual_price.to_numpy() * 100,
                "directional_accuracy": direction,
                "hit_rate": wins,
                "delta": absolute - base_absolute,
            }
        )
        .groupby("session", sort=True)
        .mean()
    )
    indices = block_indices(len(values), repetitions)
    samples = values.to_numpy()[indices].mean(axis=1)
    point = values.mean()
    results = {
        "n_predictions": len(merged),
        "n_sessions": len(values),
        "mae": float(point.mae),
        "rmse": float(np.sqrt(point.mse)),
        "mape": float(point.mape),
        "directional_accuracy": float(point.directional_accuracy),
        "hit_rate": float(point.hit_rate),
        "mae_difference_vs_random_walk": float(point.delta),
        "uncertainty_method": "paired circular moving-block bootstrap; five-session blocks, all tickers kept together",
        "bootstrap_samples": repetitions,
    }
    for name, column in (
        ("mae", 0),
        ("rmse", 1),
        ("mape", 2),
        ("directional_accuracy", 3),
        ("hit_rate", 4),
    ):
        distribution = np.sqrt(samples[:, column]) if name == "rmse" else samples[:, column]
        results[f"{name}_ci95"] = np.quantile(distribution, [0.025, 0.975]).tolist()
    results["difference_ci95"] = np.quantile(samples[:, 5], [0.025, 0.975]).tolist()
    centered = samples[:, 5] - point.delta
    results["paired_p_value"] = (
        float((np.sum(np.abs(centered) >= abs(point.delta)) + 1) / (repetitions + 1))
        if np.any(absolute != base_absolute)
        else 1.0
    )
    return results


@dataclass
class ValidationResult:
    predictions: pd.DataFrame
    metrics: dict
    forecast: list[dict]
    folds: list[dict]


class NextSessionModel:
    """No model is selected using the held-out leaderboard; forecast = fixed pooled all/Ridge."""

    def __init__(
        self,
        bootstrap_samples: int = 400,
        min_train_sessions: int = 65,
        test_sessions: int = 45,
        refit_every: int = 5,
    ):
        self.bootstrap_samples = bootstrap_samples
        self.min_train_sessions, self.test_sessions, self.refit_every = (
            min_train_sessions,
            test_sessions,
            refit_every,
        )

    def train(self, frame: pd.DataFrame) -> ValidationResult:
        sessions = sorted(frame.loc[frame.target_log_return.notna(), "session"].unique())
        if len(sessions) <= self.min_train_sessions:
            raise ValueError(
                f"Need more than {self.min_train_sessions} labelled feature sessions; found {len(sessions)}"
            )
        tests = sessions[max(self.min_train_sessions, len(sessions) - self.test_sessions) :]
        universe = sorted(frame.ticker.unique())
        variants = [
            (f"{kind}_{subset}", kind, subset, "pooled")
            for kind in ("ridge", "boost")
            for subset in FEATURE_SETS
        ]
        variants += [
            (f"per_ticker_{kind}_{subset}", kind, subset, "per_ticker")
            for kind in ("ridge", "boost")
            for subset in ("price_only", "all")
        ]
        output, folds, fitted = [], [], {}
        for index, session in enumerate(tests):
            train = causal_training_rows(frame, session)
            test = frame[(frame.session == session) & frame.target_log_return.notna()]
            if index % self.refit_every == 0:
                folds.append(
                    {
                        "test_start": session,
                        "max_feature_session": train.session.max(),
                        "max_label_session": train.target_session.max(),
                        "train_rows": len(train),
                        "training_social_rows": int(train.social_available.sum()),
                        "training_news_rows": int(train.news_available.sum()),
                    }
                )
                for name, kind, subset, scope in variants:
                    groups = (
                        [("all", train)] if scope == "pooled" else list(train.groupby("ticker"))
                    )
                    for group_name, group in groups:
                        model = estimator(kind)
                        model.fit(
                            design_matrix(group, FEATURE_SETS[subset], universe),
                            group.target_log_return,
                        )
                        fitted[(name, group_name)] = model
            for name, _, subset, scope in variants:
                for ticker, group in test.groupby("ticker"):
                    model = fitted[(name, "all" if scope == "pooled" else ticker)]
                    predicted_return = np.clip(
                        model.predict(design_matrix(group, FEATURE_SETS[subset], universe)),
                        -0.5,
                        0.5,
                    )
                    for (_, row), prediction in zip(
                        group.iterrows(), predicted_return, strict=True
                    ):
                        output.append(
                            {
                                "model": name,
                                "session": session,
                                "ticker": ticker,
                                "target_session": row.target_session,
                                "close": float(row.close),
                                "actual_price": float(row.actual_price),
                                "predicted_price": float(row.close * np.exp(prediction)),
                                "actual_log_return": float(row.target_log_return),
                            }
                        )
            for _, row in test.iterrows():
                mean_return = float(
                    train.loc[train.ticker == row.ticker, "target_log_return"].mean()
                )
                for name, prediction in (("random_walk", 0.0), ("mean_return", mean_return)):
                    output.append(
                        {
                            "model": name,
                            "session": session,
                            "ticker": row.ticker,
                            "target_session": row.target_session,
                            "close": float(row.close),
                            "actual_price": float(row.actual_price),
                            "predicted_price": float(row.close * np.exp(prediction)),
                            "actual_log_return": float(row.target_log_return),
                        }
                    )
        predictions = pd.DataFrame(output)
        baseline = predictions[predictions.model == "random_walk"]
        statistics = {
            name: metrics(group, baseline, self.bootstrap_samples)
            for name, group in predictions.groupby("model")
        }
        statistics["methodology"] = {
            "split": "expanding-window, all tickers share held-out sessions",
            "refit_every_sessions": self.refit_every,
            "forecast_model": "ridge_all"
            if frame.social_available.sum() + frame.news_available.sum() > 0
            else "ridge_price_only",
            "hyperparameters": "fixed before evaluation; no held-out tuning",
            "zero_return_baseline": "identical to random_walk, not counted twice",
            "significance_note": "Exploratory unadjusted paired block-bootstrap comparisons. Cross-model multiple testing is not corrected.",
            "social_labelled_sessions": int(frame.groupby("session").social_available.max().sum()),
            "news_labelled_sessions": int(frame.groupby("session").news_available.max().sum()),
        }
        return ValidationResult(predictions, statistics, self.forecast(frame, predictions), folds)

    def forecast(
        self, frame: pd.DataFrame, historical_predictions: pd.DataFrame | None = None
    ) -> list[dict]:
        latest = frame.groupby("ticker", sort=True).tail(1).copy()
        cutoff = str(latest.session.max())
        train = frame[frame.target_log_return.notna() & (frame.target_session <= cutoff)]
        universe = sorted(frame.ticker.unique())
        model = estimator("ridge")
        subset = (
            "all" if train.social_available.sum() + train.news_available.sum() > 0 else "price_only"
        )
        forecast_name = f"ridge_{subset}"
        model.fit(design_matrix(train, FEATURE_SETS[subset], universe), train.target_log_return)
        predicted = np.clip(
            model.predict(design_matrix(latest, FEATURE_SETS[subset], universe)), -0.5, 0.5
        )
        residuals = np.array([-0.04, 0.04])
        if historical_predictions is not None:
            heldout = historical_predictions[historical_predictions.model == forecast_name]
            residuals = np.log(heldout.actual_price / heldout.predicted_price).to_numpy()
        lower, upper = np.quantile(residuals, [0.025, 0.975])
        return [
            {
                "ticker": row.ticker,
                "feature_session": row.session,
                "target_session": row.target_session,
                "current_price": float(row.close),
                "predicted_price": float(row.close * np.exp(value)),
                "change_pct": float(np.expm1(value) * 100),
                "lower_price": float(row.close * np.exp(value + lower)),
                "upper_price": float(row.close * np.exp(value + upper)),
                "model_name": forecast_name,
                "model_trained_through": str(train.target_session.max()),
                "interval_note": "Empirical 95% held-out residual band, not a guaranteed calibrated prediction interval",
            }
            for (_, row), value in zip(latest.iterrows(), predicted, strict=True)
        ]
