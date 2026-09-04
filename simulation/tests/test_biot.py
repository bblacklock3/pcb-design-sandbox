"""Biot-Savart primitives against closed-form results."""
import numpy as np
import pytest
from scipy.special import ellipe, ellipk

from indsim import biot
from indsim.biot import MU0, Segments


def circle(radius, z=0.0, n=720, sense=1.0):
    """Closed circular polyline of `n` segments as a Segments object (unit current)."""
    th = np.linspace(0.0, 2 * np.pi, n + 1)
    pts = np.column_stack([radius * np.cos(th), radius * np.sin(th), np.full_like(th, z)])
    return Segments.from_polyline(pts, weight=sense)


def test_segments_from_polyline_closes_loop():
    pts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    s = Segments.from_polyline(pts, weight=2.0, closed=True)
    assert s.p0.shape == (4, 3)
    np.testing.assert_allclose(s.p1[-1], pts[0])
    np.testing.assert_allclose(s.w, 2.0)
    assert s.length() == pytest.approx(4.0)


def test_circular_loop_centre_field():
    R = 0.010
    loop = circle(R)
    b = biot.bfield(loop, np.array([[0.0, 0.0, 0.0]]))
    assert b.shape == (1, 3)
    np.testing.assert_allclose(b[0, :2], 0.0, atol=1e-15)
    assert b[0, 2] == pytest.approx(MU0 / (2 * R), rel=1e-4)


def test_circular_loop_on_axis_field():
    R = 0.010
    z = 0.007
    loop = circle(R)
    b = biot.bfield(loop, np.array([[0.0, 0.0, z]]))
    expected = MU0 * R**2 / (2 * (R**2 + z**2) ** 1.5)
    assert b[0, 2] == pytest.approx(expected, rel=1e-4)


def test_long_straight_segment_field():
    L = 2.0
    d = 0.01
    seg = Segments(np.array([[-L / 2, 0, 0]]), np.array([[L / 2, 0, 0]]), np.array([1.0]))
    b = biot.bfield(seg, np.array([[0.0, d, 0.0]]))
    # +x current, point on +y: B is along +z (right-hand rule)
    assert b[0, 2] == pytest.approx(MU0 / (2 * np.pi * d), rel=1e-3)
    np.testing.assert_allclose(b[0, :2], 0.0, atol=1e-15)


def test_field_scales_with_weight_and_reverses_with_sense():
    R = 0.010
    b1 = biot.bfield(circle(R), np.zeros((1, 3)))
    b3 = biot.bfield(circle(R, sense=3.0), np.zeros((1, 3)))
    bneg = biot.bfield(circle(R, sense=-1.0), np.zeros((1, 3)))
    np.testing.assert_allclose(b3, 3 * b1)
    np.testing.assert_allclose(bneg, -b1)


def test_field_many_points_chunked_matches_unchunked():
    loop = circle(0.010, n=200)
    pts = np.random.default_rng(0).normal(size=(1000, 3)) * 0.02
    a = biot.bfield(loop, pts, chunk=64)
    b = biot.bfield(loop, pts, chunk=10_000)
    np.testing.assert_allclose(a, b, rtol=1e-12)


def coaxial_mutual(R1, R2, d):
    k2 = 4 * R1 * R2 / ((R1 + R2) ** 2 + d**2)
    k = np.sqrt(k2)
    return MU0 * np.sqrt(R1 * R2) * ((2 / k - k) * ellipk(k2) - (2 / k) * ellipe(k2))


def test_coaxial_loops_mutual_inductance():
    R1, R2, d = 0.010, 0.008, 0.005
    M = biot.mutual_inductance(circle(R1), circle(R2, z=d))
    assert M == pytest.approx(coaxial_mutual(R1, R2, d), rel=2e-3)


def test_mutual_inductance_is_symmetric_and_signed():
    a, b = circle(0.010), circle(0.006, z=0.004)
    assert biot.mutual_inductance(a, b) == pytest.approx(biot.mutual_inductance(b, a), rel=1e-12)
    assert biot.mutual_inductance(a, circle(0.006, z=0.004, sense=-1)) == pytest.approx(
        -biot.mutual_inductance(a, b), rel=1e-12
    )


def test_self_inductance_of_circular_loop():
    R, a = 0.010, 0.0001
    L = biot.self_inductance(circle(R, n=2000), wire_radius=a)
    expected = MU0 * R * (np.log(8 * R / a) - 2)
    assert L == pytest.approx(expected, rel=1e-3)


def test_mirror_z_reflects_about_plane_and_reverses_sense():
    loop = circle(0.010, z=0.001)
    img = biot.mirror(loop, plane_z=-0.002)
    np.testing.assert_allclose(img.p0[:, 2], -0.005)
    np.testing.assert_allclose(img.p0[:, :2], loop.p0[:, :2])
    np.testing.assert_allclose(img.w, -loop.w)


def test_image_plane_cancels_normal_field_on_plane():
    loop = circle(0.010, z=0.003)
    img = biot.mirror(loop, plane_z=0.0)
    pts = np.array([[0.002, 0.001, 0.0], [0.015, -0.004, 0.0]])
    b = biot.bfield(loop, pts) + biot.bfield(img, pts)
    np.testing.assert_allclose(b[:, 2], 0.0, atol=1e-12)


def test_ac_resistance_uses_skin_depth():
    # 1 m of 6 mil (152.4 um) x 35 um copper at 3 MHz: skin depth ~38 um > thickness,
    # so resistance is close to DC.
    r_dc = 1.68e-8 / (152.4e-6 * 35e-6)
    r_ac = biot.trace_resistance(length=1.0, width=152.4e-6, thickness=35e-6, freq=3e6)
    assert r_ac >= r_dc
    assert r_ac == pytest.approx(r_dc, rel=0.5)
    r_hi = biot.trace_resistance(length=1.0, width=152.4e-6, thickness=35e-6, freq=300e6)
    assert r_hi > 3 * r_dc


def test_refine_splits_long_segments_and_preserves_path():
    sq = Segments.from_polyline(np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]) * 1e-3)
    fine = biot.refine(sq, 0.1e-3)
    assert len(fine) == 40
    assert fine.length() == pytest.approx(sq.length())
    np.testing.assert_allclose(fine.p0[0], sq.p0[0])
    np.testing.assert_allclose(fine.p1[9], sq.p1[0])
    np.testing.assert_allclose(fine.w, 1.0)


def test_self_inductance_of_coarse_square_matches_fine_square():
    a = 7.6e-5
    pts = np.array([[-9, -4.8, 0], [9, -4.8, 0], [9, 4.8, 0], [-9, 4.8, 0]]) * 1e-3
    coarse = Segments.from_polyline(pts)
    L = biot.self_inductance(coarse, a)
    # Grover's rectangle formula (thin wire, high-frequency current)
    x, y, r = 18e-3, 9.6e-3, a
    d = np.hypot(x, y)
    expected = (MU0 / np.pi) * (
        -2 * (x + y) + 2 * d - x * np.log((x + d) / y) - y * np.log((y + d) / x) + x * np.log(2 * x / r) + y * np.log(2 * y / r)
    )
    assert L == pytest.approx(expected, rel=0.02)


def test_mutual_inductance_refines_coarse_input():
    pts = np.array([[-9, -4.8, 0], [9, -4.8, 0], [9, 4.8, 0], [-9, 4.8, 0]]) * 1e-3
    coarse = Segments.from_polyline(pts)
    other = circle(0.003, z=0.0012, n=200)
    m_coarse = biot.mutual_inductance(coarse, other)
    m_fine = biot.mutual_inductance(biot.refine(coarse, 2e-5), other, max_len=2e-5)
    assert m_coarse == pytest.approx(m_fine, rel=1e-3)
