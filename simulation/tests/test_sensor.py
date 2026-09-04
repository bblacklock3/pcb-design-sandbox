"""Angle, counts, linearity and linearisation maths on synthetic flux."""
import numpy as np
import pytest

from indsim import sensor


def test_ideal_quadrature_gives_zero_linearity_error():
    lam = 15.0
    x = np.linspace(0.0, 10.5, 211)
    phi_sin = 3e-9 * np.sin(2 * np.pi * x / lam + 0.7)
    phi_cos = 3e-9 * np.cos(2 * np.pi * x / lam + 0.7)
    ang = sensor.electrical_angle(phi_sin, phi_cos)
    assert np.all(np.diff(ang) > 0)  # unwrapped, monotonic
    assert ang[-1] - ang[0] == pytest.approx(2 * np.pi * 10.5 / lam, rel=1e-9)
    lin = sensor.linearity(x, ang)
    assert lin["max_abs"] < 1e-9
    assert lin["slope"] == pytest.approx(2 * np.pi / lam, rel=1e-9)


def test_counts_scale_to_4096_per_period_with_optional_reserve():
    ang = np.array([0.0, np.pi, 2 * np.pi])
    np.testing.assert_allclose(sensor.counts(ang), [0.0, 2048.0, 4096.0])
    np.testing.assert_allclose(sensor.counts(ang, reserve=0.1), [409.6, 2048.0, 3686.4])


def test_piecewise_correction_removes_matching_piecewise_error():
    y_meas = np.linspace(0.0, 1.0, 501)
    knots = np.linspace(0.0, 1.0, 11)
    rng = np.random.default_rng(1)
    d_knots = rng.normal(scale=0.02, size=11)
    y_ref = y_meas + np.interp(y_meas, knots, d_knots)
    y_corr = sensor.piecewise_correct(y_meas, y_ref, n_seg=10)
    np.testing.assert_allclose(y_corr, y_ref, atol=1e-9)


def test_piecewise_correction_reduces_smooth_error():
    y_meas = np.linspace(0.0, 1.0, 501)
    y_ref = y_meas + 0.01 * np.sin(3 * 2 * np.pi * y_meas)
    before = np.abs(y_meas - y_ref).max()
    after = np.abs(sensor.piecewise_correct(y_meas, y_ref, n_seg=10) - y_ref).max()
    assert after < before / 3  # 10 segments across 3 cycles: ~3.4x measured


def test_harmonics_recovers_known_content():
    th = np.linspace(0.0, 2 * np.pi, 721)[:-1]
    err = 0.010 * np.sin(3 * th) + 0.004 * np.cos(1 * th + 0.3)
    h = sensor.harmonics(th, err, n_max=6)
    assert h[3] == pytest.approx(0.010, rel=1e-6)
    assert h[1] == pytest.approx(0.004, rel=1e-6)
    assert h[2] < 1e-9 and h[4] < 1e-9


def test_linearity_reports_residual_against_best_fit_line():
    x = np.linspace(0, 10, 101)
    y = 0.5 * x + 3.0 + 0.1 * np.sin(2 * np.pi * x / 10)
    lin = sensor.linearity(x, y)
    assert lin["residual"].shape == x.shape
    # the best-fit line absorbs part of a one-cycle sinusoid, so the peak is a bit under 0.1
    assert lin["max_abs"] == pytest.approx(0.093, rel=0.03)
    # residual is what remains after the best-fit line, so its mean is ~0
    assert abs(lin["residual"].mean()) < 1e-9


def test_tank_estimate_for_a_plain_loop():
    from indsim import geometry as g

    tx = g.rect_tx(len_mm=18.0, wid_mm=9.6, n_turns=4, pitch_mm=0.3048, layers_z_mm=(-1.4, -1.6))
    t = sensor.tank(tx, c_tank=600e-12)
    assert 1e-7 < t["L"] < 1e-5
    assert t["f0"] == pytest.approx(1 / (2 * np.pi * np.sqrt(t["L"] * 600e-12)), rel=1e-9)
    assert t["Q"] > 1
    backed = sensor.tank(tx, c_tank=600e-12, plane=g.ImagePlane(z_mm=-2.0))
    assert backed["L"] < t["L"]
