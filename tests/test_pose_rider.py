"""Tests for trapezium-based seated rider detection."""
import numpy as np

from services.association.pose_rider import (
    is_seated_on_motorcycle,
    motorcycle_seat_trapezium,
    seated_overlap_score,
)


def test_standing_officer_not_seated():
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    bike = [300, 280, 520, 520]
    standing = [120, 120, 220, 520]
    assert not is_seated_on_motorcycle(image, standing, bike)


def test_rider_on_seat_trapezium():
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    bike = [300, 280, 520, 520]
    rider = [360, 180, 460, 400]
    assert is_seated_on_motorcycle(image, rider, bike)
    assert seated_overlap_score(rider, bike) > 0.2


def test_trapezium_has_four_corners():
    trap = motorcycle_seat_trapezium([0, 0, 100, 200])
    assert trap.shape == (4, 2)
