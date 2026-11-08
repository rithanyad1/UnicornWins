from app.ai.anomaly_detector import AnomalyDetector


def test_untrained_model_does_not_make_production_prediction() -> None:
    result = AnomalyDetector().detect([{"temperature_c": 24}])
    assert result["model_trained"] is False
    assert result["anomaly_detected"] is False
    assert result["recommended_action"] == "MODEL_NOT_TRAINED"


def test_isolation_forest_training_detection_and_model_reload(tmp_path) -> None:
    detector = AnomalyDetector()
    detector.train_simulated()
    normal = detector.detect([{
        "temperature_c": 24, "humidity_percent": 48, "vibration_score": 0.1,
    }])
    anomalous = detector.detect([{
        "temperature_c": 90, "humidity_percent": 99, "vibration_score": 12,
    }])
    assert normal["model_trained"] is True
    assert anomalous["anomaly_detected"] is True
    assert isinstance(anomalous["anomaly_score"], float)
    assert anomalous["suspected_factors"]

    model_path = tmp_path / "isolation_forest.joblib"
    detector.save(model_path)
    loaded = AnomalyDetector(model_path)
    assert loaded.is_trained
    assert loaded.detect([{
        "temperature_c": 90, "humidity_percent": 99, "vibration_score": 12,
    }])["anomaly_detected"] is True