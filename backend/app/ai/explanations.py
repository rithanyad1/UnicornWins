from typing import Any


def explain_anomaly(reading: dict[str, Any], history: list[dict[str, Any]]) -> list[str]:
    factors: list[str] = []
    temperature = float(reading.get("temperature_c", 25))
    humidity = float(reading.get("humidity_percent", 50))
    vibration = float(reading.get("vibration_score", 0))
    if temperature >= 35:
        factors.append("Temperature exceeds the configured high-temperature range")
    if humidity >= 70:
        factors.append("Humidity exceeds the configured high-humidity range")
    if vibration >= 0.7:
        factors.append("Vibration is above the calibrated normal range")
    if len(history) >= 2:
        older, newer = history[-2], history[-1]
        if float(newer.get("temperature_c", 0)) - float(older.get("temperature_c", 0)) >= 3:
            factors.append("Rapid temperature increase")
        if float(newer.get("humidity_percent", 0)) - float(older.get("humidity_percent", 0)) >= 10:
            factors.append("Rapid humidity increase")
    if reading.get("water_detected"):
        factors.append("Water sensor is active")
    return factors or ["Environmental feature combination differs from the learned baseline"]


def recommend_action(reading: dict[str, Any]) -> str:
    if reading.get("water_detected"):
        return "BUZZER_ON"
    if float(reading.get("temperature_c", 0)) >= 35:
        return "FAN_ON"
    if float(reading.get("vibration_score", 0)) >= 0.7:
        return "BUZZER_ON"
    return "INVESTIGATE"