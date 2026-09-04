"""Geometry generators: balance, counts, units."""
import numpy as np
import pytest

from indsim import geometry as g
from indsim.geometry import MM


def test_mm_round_trip():
    assert g.mm(12.5) == pytest.approx(0.0125)
    assert g.to_mm(g.mm(12.5)) == pytest.approx(12.5)
    assert MM == 1e-3


def test_loop_signed_area_ccw_square_positive():
    sq = g.Loop(np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]) * MM, sense=1)
    assert sq.signed_area() == pytest.approx(1e-6)
    assert g.Loop(sq.pts, sense=-1).signed_area() == pytest.approx(-1e-6)
    assert sq.segments().w.tolist() == [1.0] * 4


def test_linear_rx_pair_has_zero_net_area_and_lobes_alternate():
    sin_c, cos_c = g.linear_rx_pair(lam_mm=15.0, lobe_width_mm=7.6, n_lobes=2, layers_z_mm=(0.0, -0.2))
    lobe_area = 2 * 3.8 * MM * 15.0 * MM / np.pi  # area of one |sin| lobe: 2A * lambda/pi ... per half period
    for c in (sin_c, cos_c):
        assert abs(c.net_signed_area()) < 1e-3 * lobe_area
        # one figure-8 loop, spans both layers
        zs = np.unique(np.round(c.segments().p0[:, 2] / MM, 6))
        assert set(zs.tolist()) == {0.0, -0.2}
    # travel axis is x; coil spans one full period centred on the origin
    p = sin_c.segments().p0
    assert p[:, 0].min() == pytest.approx(-7.5 * MM, abs=1e-6)
    assert p[:, 0].max() == pytest.approx(7.5 * MM, abs=1e-6)
    assert p[:, 1].max() == pytest.approx(3.8 * MM, rel=1e-3)
    # sine coil is antisymmetric about x = 0 in its lobe sign; cosine coil is symmetric.
    # Probe with the Bz produced at two mirror-image points above the coil.
    from indsim import biot

    pts = np.array([[-3.75, 0, 1.0], [3.75, 0, 1.0]]) * MM
    bs = biot.bz(sin_c.segments(), pts)
    bc = biot.bz(cos_c.segments(), pts)
    assert bs[0] == pytest.approx(-bs[1], rel=1e-6)
    assert bc[0] == pytest.approx(bc[1], rel=1e-6)
    assert abs(bs[0]) > 0 and abs(bc[0]) > 0


def test_rect_tx_turn_count_sense_and_layers():
    tx = g.rect_tx(len_mm=18.0, wid_mm=9.6, n_turns=4, pitch_mm=0.3048, layers_z_mm=(-1.4, -1.6), corner_r_mm=1.0)
    assert len(tx.loops) == 8
    assert all(l.sense == 1 for l in tx.loops)
    zs = sorted(set(round(l.pts[0, 2] / MM, 6) for l in tx.loops))
    assert zs == [-1.6, -1.4]
    outer = max(tx.loops, key=lambda l: l.signed_area())
    assert outer.pts[:, 0].max() - outer.pts[:, 0].min() == pytest.approx(18.0 * MM, rel=1e-6)
    assert outer.pts[:, 1].max() - outer.pts[:, 1].min() == pytest.approx(9.6 * MM, rel=1e-6)
    inner = min(tx.loops, key=lambda l: l.signed_area())
    assert inner.pts[:, 0].max() - inner.pts[:, 0].min() == pytest.approx((18.0 - 6 * 0.3048) * MM, rel=1e-6)
    assert tx.turns() == 8
    assert tx.length() > 8 * 2 * (18.0 + 9.6 - 6 * 0.3048) * MM * 0.9


def test_ring_rx_pair_zero_net_area_and_periodicity():
    sin_c, cos_c = g.ring_rx_pair(r_in_mm=17.0, r_out_mm=29.0, n_periods=2, layers_z_mm=(0.0, -0.2))
    for c in (sin_c, cos_c):
        assert abs(c.net_signed_area()) < 1e-6 * np.pi * (29e-3) ** 2
        r = np.hypot(c.segments().p0[:, 0], c.segments().p0[:, 1])
        assert r.min() == pytest.approx(17.0 * MM, rel=1e-3)
        assert r.max() == pytest.approx(29.0 * MM, rel=1e-3)
    from indsim import biot

    # Bz above the ring at angle theta repeats every 180 deg for N = 2 and flips at 90 deg.
    def probe(coil, th_deg):
        th = np.deg2rad(th_deg)
        return biot.bz(coil.segments(), np.array([[23 * np.cos(th), 23 * np.sin(th), 1.5]]) * MM)[0]

    assert probe(sin_c, 45) == pytest.approx(probe(sin_c, 225), rel=1e-6)
    # a quarter turn swaps which layer carries the +A lobe, so the flip is exact only
    # for coincident layers; 0.2 mm of layer offset at 1.5 mm probe height gives ~0.3 %
    assert probe(sin_c, 45) == pytest.approx(-probe(sin_c, 135), rel=1e-2)
    # cosine coil is the sine coil advanced by a quarter electrical period (45 deg here)
    assert probe(cos_c, 0) == pytest.approx(probe(sin_c, 45), rel=1e-6)


def test_ring_tx_senses_and_radii():
    tx = g.ring_tx(r_in_mm=17.0, r_out_mm=29.0, n_turns=3, pitch_mm=0.3, layers_z_mm=(-1.0,))
    assert len(tx.loops) == 6
    outer = [l for l in tx.loops if np.hypot(*l.pts[0, :2]) > 25 * MM]
    inner = [l for l in tx.loops if np.hypot(*l.pts[0, :2]) < 20 * MM]
    assert len(outer) == 3 and len(inner) == 3
    assert all(l.sense == 1 for l in outer) and all(l.sense == -1 for l in inner)
    assert tx.turns() == 6


def test_rect_sheet_mesh_area_and_z():
    sh = g.rect_sheet(lx_mm=5.0, ly_mm=10.0, a_mm=0.5, z_mm=1.0)
    assert sh.n == 200
    assert sh.area() == pytest.approx(50e-6)
    np.testing.assert_allclose(sh.centers[:, 2], 1.0 * MM)
    loops = sh.cell_loops()
    assert len(loops) == 4 * sh.n
    # each cell loop is CCW seen from +z: positive signed area a^2
    quad = loops.p0[:4]
    x, y = quad[:, 0], quad[:, 1]
    area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
    assert area == pytest.approx((0.5 * MM) ** 2)


def test_sheet_translate_and_rotate():
    sh = g.rect_sheet(lx_mm=5.0, ly_mm=10.0, a_mm=0.5, z_mm=1.0)
    moved = sh.translated_mm((2.0, 0.0, 0.5))
    np.testing.assert_allclose(moved.centers.mean(axis=0), np.array([2.0, 0.0, 1.5]) * MM, atol=1e-12)
    rot = sh.rotated(np.pi / 2)
    ext = rot.centers.max(axis=0) - rot.centers.min(axis=0)
    assert ext[0] == pytest.approx(9.5 * MM) and ext[1] == pytest.approx(4.5 * MM)
    # rotation keeps every cell square and CCW
    q = rot.cell_loops().p0[:4]
    x, y = q[:, 0], q[:, 1]
    assert 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) == pytest.approx((0.5 * MM) ** 2)
    # K-matrix invariance relies on rotation preserving the cell-to-cell geometry
    d0 = np.linalg.norm(sh.centers[1] - sh.centers[0])
    d1 = np.linalg.norm(rot.centers[1] - rot.centers[0])
    assert d0 == pytest.approx(d1)


def test_sector_sheet_area_and_count():
    sh = g.sector_sheet(r1_mm=15.0, r2_mm=31.0, angle_deg=60.0, k=2, a_mm=0.5, z_mm=2.0)
    expected = 2 * (60 / 360) * np.pi * ((31e-3) ** 2 - (15e-3) ** 2)
    assert sh.area() == pytest.approx(expected, rel=0.03)
    ang = np.degrees(np.arctan2(sh.centers[:, 1], sh.centers[:, 0])) % 360
    # two sectors centred on 0 deg and 180 deg
    assert np.all((ang < 31) | (ang > 329) | ((ang > 149) & (ang < 211)))


def test_disc_sheet_with_hole_and_slots():
    sh = g.disc_sheet(r_out_mm=35.0, a_mm=1.0, z_mm=-3.0, r_hole_mm=15.0)
    assert sh.area() == pytest.approx(np.pi * ((35e-3) ** 2 - (15e-3) ** 2), rel=0.02)
    slotted = g.disc_sheet(r_out_mm=35.0, a_mm=1.0, z_mm=-3.0, r_hole_mm=15.0, n_slots=18, slot_deg=5.0)
    assert slotted.area() == pytest.approx(sh.area() * 0.75, rel=0.05)


def test_image_plane_holds_z():
    p = g.ImagePlane(z_mm=-4.0)
    assert p.z == pytest.approx(-4.0 * MM)


def test_coil_translate_and_mirror():
    tx = g.rect_tx(len_mm=18.0, wid_mm=9.6, n_turns=1, pitch_mm=0.3, layers_z_mm=(-1.0,))
    m = tx.mirrored(plane_z=-3.0 * MM)
    assert m.loops[0].pts[0, 2] == pytest.approx(-5.0 * MM)
    assert m.loops[0].sense == -1
    t = tx.translated_mm((1.0, 2.0, 0.0))
    assert t.loops[0].pts[:, 0].mean() == pytest.approx(1.0 * MM, abs=1e-9)


def test_sheet_union_keeps_cell_sizes_and_areas():
    a = g.rect_sheet(lx_mm=4.0, ly_mm=4.0, a_mm=0.5, z_mm=1.0)
    b = g.disc_sheet(r_out_mm=10.0, a_mm=1.0, z_mm=-3.0, r_hole_mm=5.0)
    u = a.union(b)
    assert u.n == a.n + b.n
    assert u.area() == pytest.approx(a.area() + b.area())
    assert len(u.cell_loops()) == 4 * u.n
    with pytest.raises(ValueError):
        _ = u.a
    assert g.union([a, b]).n == u.n


def test_coil_rotation_is_rigid():
    sin_c, _ = g.ring_rx_pair(r_in_mm=17.0, r_out_mm=29.0, n_periods=2, layers_z_mm=(0.0, -1.0))
    r = sin_c.rotated_deg(37.0)
    assert r.length() == pytest.approx(sin_c.length())
    p0 = sin_c.loops[0].pts[0]
    p1 = r.loops[0].pts[0]
    assert np.hypot(*p1[:2]) == pytest.approx(np.hypot(*p0[:2]))
    assert np.degrees(np.arctan2(p1[1], p1[0]) - np.arctan2(p0[1], p0[0])) == pytest.approx(37.0)
    assert p1[2] == pytest.approx(p0[2])
