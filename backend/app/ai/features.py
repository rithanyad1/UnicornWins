from collections.abc import Sequence
from typing import Any

FEATURE_NAMES = (
    "temperature_c",
    "humidity_percent",
    "vibration_score",
    "temperature_rate",
    "humidity_rate",
)


def extract_features(history: Sequence[dict[str, Any]]) -> list[float]:
    if not history:
        raise ValueError("At least one sensor reading is required")
    current = history[-1]
    previous = history[-2] if len(history) > 1 else current
    temperature = _number(current.get("temperature_c"), 25.0)
    humidity = _number(current.get("humidity_percent"), 50.0)
    vibration = _number(current.get("vibration_score"), 0.0)
    previous_temperature = _number(previous.get("temperature_c"), temperature)
    previous_humidity = _number(previous.get("humidity_percent"), humidity)

    elapsed = 1.0
    current_time = current.get("recorded_at")
    previous_time = previous.get("recorded_at")
    if current_time is not None and previous_time is not None:
        try:
            elapsed = max((current_time - previous_time).total_seconds(), 0.001)
        except AttributeError:
            pass
    return [
        temperature,
        humidity,
        vibration,
        (temperature - previous_temperature) / elapsed,
        (humidity - previous_humidity) / elapsed,
    ]


def _number(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or abs(number) == float("inf"):
        return default
    return number