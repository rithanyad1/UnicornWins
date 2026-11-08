import csv
import json
from pathlib import Path
from typing import Any

from app.ai.anomaly_detector import AnomalyDetector


def load_baseline(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Baseline data file not found: {source}")
    if source.suffix.lower() == ".json":
        rows = json.loads(source.read_text())
    elif source.suffix.lower() == ".csv":
        with source.open(newline="") as file:
            rows = list(csv.DictReader(file))
    else:
        raise ValueError("Baseline data must be a .csv or .json file")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("Baseline data must contain a list of sensor reading objects")
    return rows


def train_from_file(path: str | Path, model_path: str | Path) -> AnomalyDetector:
    detector = AnomalyDetector()
    detector.train(load_baseline(path))
    detector.save(model_path)
    return detector