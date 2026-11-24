"""Tests for sensor anomaly detection."""

from idata2304_smart_house_project.anomaly_detector import AnomalyDetector


# Verify normal temperature
def test_normal_temperature():
    # A normal temperature should not trigger a warning
    detector = AnomalyDetector()

    assert detector.check("temperature", 22.5) is None


# Verify high temperature
def test_high_temperature():
    # A temperature above 30 degrees should trigger a warning
    detector = AnomalyDetector()

    assert detector.check(
        "temperature", 35.5
    ) == "WARNING: High temperature!"


# Verify low humidity
def test_low_humidity():
    # Humidity below 30 should trigger a warning
    detector = AnomalyDetector()

    assert detector.check(
        "humidity", 20.0
    ) == "WARNING: Low humidity!"
