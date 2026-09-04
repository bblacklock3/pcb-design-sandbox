"""Fast paths must reproduce the direct ones: Toeplitz K build, polar field tables,
solver reuse, and the parallel map."""
import numpy as np
import pytest

from indsim import biot, geometry as g, sensor, sheet, tables
from indsim.geometry import MM


def test_mesh_carries_lattice_indices_through_rigid_motion():
    sh = g.rect_sheet(lx_mm=4.0, ly_mm=3.0, a_mm=0.5, z_mm=1.0)
    assert sh.lattice.shape == (sh.n, 2)
    assert sh.lattice.dtype.kind == "i"
    # neighbours in the lattice are one cell apart in space
    d = sh.lattice[1] - sh.lattice[0]
    assert np.linalg.norm(sh.centers[1] - sh.centers[0]) == pytest.approx(0.5 * MM * np.linalg.norm(d))
    moved = sh.rotated_deg(33.0).translated_mm((5, -2, 0))
    np.testing.assert_array_equal(moved.lattice, sh.lattice)
    assert np.all(moved.block == 0)


def test_toeplitz_k_matches_direct_for_rect_and_rotated_sector():
    for sh in (
        g.rect_sheet(lx_mm=5.0, ly_mm=10.0, a_mm=0.5, z_mm=1.0),
        g.sector_sheet(r1_mm=15.0, r2_mm=31.0, angle_deg=60.0, k=2, a_mm=1.5, z_mm=2.0).rotated_deg(17.0).translated_mm((0.3, 0, 0)),
    ):
        K_fast = sheet.build_k(sh)
        K_direct = sheet.build_k_direct(sh)
        np.testing.assert_allclose(K_fast, K_direct, rtol=1e-10, atol=1e-13 * np.abs(K_direct).max())


def test_toeplitz_k_matches_direct_with_image_plane():
    sh = g.sector_sheet(r1_mm=15.0, r2_mm=31.0, angle_deg=60.0, k=2, a_mm=1.5, z_mm=2.0)
    plane = g.ImagePlane(z_mm=-2.5)
    K_direct = sheet.build_k_direct(sh, plane)
    np.testing.assert_allclose(sheet.build_k(sh, plane), K_direct, rtol=1e-10, atol=1e-13 * np.abs(K_direct).max())


def test_union_k_uses_blocks_and_matches_direct():
    a = g.rect_sheet(lx_mm=4.0, ly_mm=4.0, a_mm=0.5, z_mm=1.0)
    b = g.disc_sheet(r_out_mm=8.0, a_mm=1.0, z_mm=-3.0, r_hole_mm=4.0)
    u = a.union(b)
    assert set(np.unique(u.block).tolist()) == {0, 1}
    K_direct = sheet.build_k_direct(u)
    np.testing.assert_allclose(sheet.build_k(u), K_direct, rtol=1e-10, atol=1e-13 * np.abs(K_direct).max())


def test_polar_table_reproduces_direct_field():
    tx = g.ring_tx(17.0, 29.0, 1, 0.3048, (0.0, -1.0), n_theta=90)
    rx_sin, _ = g.ring_rx_pair(17.0, 29.0, 2, (0.0, -1.0), amp_mm=4.8, n_theta=180)
    rng = np.random.default_rng(3)
    r = rng.uniform(15.5, 30.5, 400) * MM
    th = rng.uniform(0, 2 * np.pi, 400)
    pts = np.column_stack([r * np.cos(th), r * np.sin(th), np.full(400, 2.0 * MM)])
    for coil, period in ((tx, 360.0 / 90), (rx_sin, 180.0)):
        tab = tables.PolarFieldTable(coil.segments(), z=2.0 * MM, r_min_mm=15.0, r_max_mm=31.0, period_deg=period, dr_mm=0.1, dtheta_deg=0.5)
        exact = biot.bz(coil.segments(), pts)
        approx = tab.bz(pts)
        err = np.abs(approx - exact).max() / np.abs(exact).max()
        assert err < 1e-3, err  # radial spacing 0.1 mm sets this; angular step barely matters
    # with a plane the table bakes in the image
    plane = g.ImagePlane(-3.0)
    tab = tables.PolarFieldTable(tx.segments(), z=2.0 * MM, r_min_mm=15.0, r_max_mm=31.0, period_deg=4.0, plane=plane)
    exact = biot.bz(tx.segments(), pts) + biot.bz(biot.mirror(tx.segments(), plane.z), pts)
    assert np.abs(tab.bz(pts) - exact).max() / np.abs(exact).max() < 1e-3


def test_sweep_with_tables_matches_direct_sweep():
    tx = g.ring_tx(17.0, 29.0, 1, 0.3048, (0.0, -1.0), n_theta=90)
    rs, rc = g.ring_rx_pair(17.0, 29.0, 2, (0.0, -1.0), amp_mm=4.8, n_theta=180)
    target = g.sector_sheet(15.0, 31.0, 60.0, 2, 1.5, 2.0)
    plane = g.ImagePlane(-2.0)
    thetas = np.array([0.0, 30.0, 75.0])
    place = lambda th: target.rotated_deg(th)  # noqa: E731
    direct = sensor.run_sweep(tx, rs, rc, place, thetas, plane=plane)
    tabs = tables.ring_tables(tx, rs, rc, target, n_periods=2, plane=plane, dr_mm=0.2, dtheta_deg=0.5)
    fast = sensor.run_sweep(tx, rs, rc, place, thetas, plane=plane, tables=tabs)
    np.testing.assert_allclose(fast["phi_sin"], direct["phi_sin"], rtol=3e-3, atol=1e-3 * direct["amplitude"].max())
    np.testing.assert_allclose(fast["phi_cos"], direct["phi_cos"], rtol=3e-3, atol=1e-3 * direct["amplitude"].max())
    assert fast["direct_sin"] == pytest.approx(direct["direct_sin"])


def _square(x):
    return x * x


def test_pmap_runs_in_processes_and_keeps_order():
    from indsim.parallel import pmap

    out = pmap(_square, [3, 1, 2], workers=2)
    assert out == [9, 1, 4]
