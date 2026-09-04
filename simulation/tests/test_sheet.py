"""Perfect-conductor sheet solver against the image method and reciprocity."""
import numpy as np
import pytest

from indsim import biot, geometry as g, sheet
from indsim.biot import Segments
from indsim.geometry import MM


def circle_segs(radius_mm, z_mm, n=360, sense=1.0):
    th = np.linspace(0.0, 2 * np.pi, n + 1)
    pts = np.column_stack([radius_mm * np.cos(th), radius_mm * np.sin(th), np.full_like(th, z_mm)]) * MM
    return Segments.from_polyline(pts, weight=sense)


@pytest.fixture(scope="module")
def big_sheet():
    return g.rect_sheet(lx_mm=50.0, ly_mm=50.0, a_mm=1.0, z_mm=0.0)


@pytest.fixture(scope="module")
def big_solver(big_sheet):
    return sheet.SheetSolver(big_sheet, keep_k=True)


def test_k_matrix_is_symmetric_with_positive_diagonal(big_solver):
    K = big_solver.K
    assert K.shape == (2500, 2500)
    np.testing.assert_allclose(K, K.T, rtol=1e-9, atol=1e-12 * np.abs(K).max())
    a = big_solver.sheet.a
    np.testing.assert_allclose(np.diag(K), 2 * np.sqrt(2) * biot.MU0 / (np.pi * a), rtol=1e-9)


def test_solution_cancels_normal_field_at_cell_centres(big_solver):
    src = circle_segs(6.0, 3.0)
    bz_src = biot.bz(src, big_solver.sheet.centers)
    psi = big_solver.solve(bz_src)
    residual = big_solver.K @ psi + bz_src
    assert np.abs(residual).max() < 1e-9 * np.abs(bz_src).max()


def test_large_sheet_reproduces_image_method(big_solver):
    """Loop above a big sheet: flux change through an observer loop from the sheet
    currents must match the image of the source, within 5 %."""
    src = circle_segs(6.0, 3.0)
    obs = circle_segs(4.0, 5.0)
    psi = big_solver.respond(src)
    from_sheet = sheet.rx_flux(big_solver.sheet, psi, obs)
    from_image = biot.mutual_inductance(biot.mirror(src, 0.0), obs)
    assert from_sheet == pytest.approx(from_image, rel=0.05)
    # and the self case: inductance drop of the source loop itself
    self_drop = sheet.rx_flux(big_solver.sheet, psi, src)
    self_image = biot.mutual_inductance(biot.mirror(src, 0.0), src)
    assert self_drop == pytest.approx(self_image, rel=0.05)
    assert self_drop < 0  # a conductor below the loop lowers its inductance


def test_distant_sheet_changes_nothing():
    far = g.rect_sheet(lx_mm=20.0, ly_mm=20.0, a_mm=1.0, z_mm=-200.0)
    solver = sheet.SheetSolver(far)
    src = circle_segs(6.0, 3.0)
    obs = circle_segs(4.0, 5.0)
    psi = solver.respond(src)
    direct = biot.mutual_inductance(src, obs)
    assert abs(sheet.rx_flux(far, psi, obs)) < 1e-6 * abs(direct)


def test_solver_reuses_factorisation_after_move(big_solver):
    moved_sheet = big_solver.sheet.translated_mm((3.0, -2.0, 0.0)).rotated(0.3)
    moved = big_solver.moved(moved_sheet)
    assert moved.K is big_solver.K and moved.lu is big_solver.lu
    src = circle_segs(6.0, 3.0)
    # translating the sheet by d and the source by d must give the same psi
    psi_a = big_solver.respond(src)
    psi_b = big_solver.moved(big_solver.sheet.translated_mm((3.0, 0.0, 0.0))).respond(src.translated(np.array([3.0, 0, 0]) * MM))
    np.testing.assert_allclose(psi_a, psi_b, rtol=1e-9, atol=1e-12 * np.abs(psi_a).max())


def test_reciprocity_of_cell_to_coil_coupling(big_sheet):
    """Flux into the observer from a unit cell loop ~ Bz of the observer at the cell centre times a^2."""
    obs = circle_segs(4.0, 5.0)
    loops = big_sheet.cell_loops()
    j = 1275  # a central cell
    cell_j = Segments(loops.p0[4 * j : 4 * j + 4], loops.p1[4 * j : 4 * j + 4], loops.w[4 * j : 4 * j + 4])
    m_exact = biot.mutual_inductance(cell_j, obs)
    m_approx = biot.bz(obs, big_sheet.centers[j : j + 1])[0] * big_sheet.a**2
    assert m_approx == pytest.approx(m_exact, rel=0.02)


def test_plane_term_added_to_k_when_image_plane_present():
    sh = g.rect_sheet(lx_mm=10.0, ly_mm=10.0, a_mm=1.0, z_mm=2.0)
    free = sheet.SheetSolver(sh, keep_k=True)
    backed = sheet.SheetSolver(sh, plane=g.ImagePlane(z_mm=-1.0), keep_k=True)
    assert not np.allclose(free.K, backed.K)
    # the image of a cell loop is 6 mm below it with reversed sense: the diagonal drops
    assert np.all(np.diag(backed.K) < np.diag(free.K))
