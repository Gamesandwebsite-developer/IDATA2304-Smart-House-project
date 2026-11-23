"""Tests for sensor anomaly detection."""

from idata2304_smart_house_project.anomaly_detector import AnomalyDetector


def test_normal_temperature():
    # A normal temperature should not trigger a warning.
    detector = AnomalyDetector()

    assert detector.check("temperature", 22.5) is None


def test_high_temperature():
    # A temperature above 30 degrees should trigger a warning.
    detector = AnomalyDetector()

    assert detector.check(
        "temperature", 35.5
    ) == "WARNING: High temperature!"


def test_low_humidity():
    # Humidity below 30 should trigger a warning.
    detector = AnomalyDetector()

    assert detector.check(
        "humidity", 20.0
    ) == "WARNING: Low humidity!"
