import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from app.ai.explanations import explain_anomaly, recommend_action
from app.ai.features import FEATURE_NAMES, extract_features

logger = logging.getLogger(__name__)


class AnomalyDetector:
    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.model: IsolationForest | None = None
        self.feature_medians: np.ndarray | None = None
        if self.model_path and self.model_path.is_file():
            try:
                self.load(self.model_path)
            except (OSError, KeyError, TypeError, ValueError):
                logger.exception("Could not load Isolation Forest model from %s", self.model_path)

    @property
    def is_trained(self) -> bool:
        return self.model is not None

    def train(self, readings: list[dict[str, Any]], *, contamination: float = 0.03) -> None:
        if len(readings) < 20:
            raise ValueError("At least 20 baseline readings are required to train the anomaly model")
        if not 0 < contamination <= 0.5:
            raise ValueError("contamination must be greater than 0 and no greater than 0.5")
        rows = np.asarray([extract_features([reading]) for reading in readings], dtype=float)
        if not np.isfinite(rows).all():
            raise ValueError("Training data contains non-finite feature values")
        self.feature_medians = np.median(rows, axis=0)
        model = IsolationForest(
            n_estimators=150,
            contamination=contamination,
            random_state=42,
        )
        model.fit(rows)
        self.model = model

    def train_simulated(self, count: int = 250) -> None:
        if count < 20:
            raise ValueError("Simulated training data must contain at least 20 samples")
        rng = np.random.default_rng(42)
        readings = [
            {
                "temperature_c": float(rng.normal(24, 1.8)),
                "humidity_percent": float(rng.normal(48, 7)),
                "vibration_score": float(max(0, rng.normal(0.12, 0.08))),
            }
            for _ in range(count)
        ]
        self.train(readings)

    def save(self, model_path: str | Path | None = None) -> Path:
        destination = Path(model_path) if model_path else self.model_path
        if destination is None:
            raise ValueError("A model path must be configured before saving")
        if self.model is None or self.feature_medians is None:
            raise RuntimeError("Cannot save an untrained anomaly model")
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.model,
            "feature_medians": self.feature_medians,
            "feature_names": FEATURE_NAMES,
        }, destination)
        self.model_path = destination
        return destination

    def load(self, model_path: str | Path) -> None:
        loaded = joblib.load(model_path)
        if tuple(loaded.get("feature_names", ())) != FEATURE_NAMES:
            raise ValueError("Saved model feature schema does not match this backend version")
        self.model = loaded["model"]
        self.feature_medians = np.asarray(loaded["feature_medians"], dtype=float)
        self.model_path = Path(model_path)

    def detect(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        if not history:
            raise ValueError("At least one sensor reading is required")
        reading = history[-1]
        if self.model is None:
            return {
                "anomaly_detected": False,
                "anomaly_score": None,
                "severity": "INFO",
                "suspected_factors": [],
                "recommended_action": "MODEL_NOT_TRAINED",
                "model_trained": False,
            }
        features = np.asarray(extract_features(history), dtype=float).reshape(1, -1)
        if self.feature_medians is not None:
            invalid = ~np.isfinite(features)
            features[invalid] = np.broadcast_to(self.feature_medians, features.shape)[invalid]
        predicted = self.model.predict(features)[0] == -1
        score = float(self.model.score_samples(features)[0])
        factors = explain_anomaly(reading, history)
        return {
            "anomaly_detected": bool(predicted),
            "anomaly_score": score,
            "severity": "WARNING" if predicted else "INFO",
            "suspected_factors": factors if predicted else [],
            "recommended_action": recommend_action(reading) if predicted else None,
            "model_trained": True,
        }