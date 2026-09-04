"""Run independent study conditions in separate processes, within a machine-wide budget.

numpy's elementwise kernels are single-threaded, so a sequential study runs on one core.
`pmap` fans conditions out to worker processes. Every worker holds its own factorised K
(about 8 bytes x n^2, so 650 MB at 9000 cells) plus field tables and kernel temporaries,
so the number of workers is bounded by RAM, not cores, and the bound is shared between
concurrent studies through a small registry file: a second study started while one is
running gets only what is left of the budget. Functions and arguments must be picklable
(module-level functions; on Windows the calling script is re-imported under `__mp_main__`).
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Iterable, Sequence

MEM_PER_WORKER = 2.0e9        # bytes; K + LU at the 9000-cell cap plus tables and temporaries
RAM_FRACTION = 0.5            # of physical RAM the simulations may use in total
REGISTRY = os.path.join(tempfile.gettempdir(), "indsim_workers.json")


def total_ram_bytes() -> int:
    if sys.platform == "win32":
        class MemStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        st = MemStatus()
        st.dwLength = ctypes.sizeof(MemStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
        return int(st.ullTotalPhys)
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return 16 * 2**30


def machine_budget() -> int:
    """Total simulation workers this machine should run at once, all studies included."""
    by_ram = int(RAM_FRACTION * total_ram_bytes() / MEM_PER_WORKER)
    by_cpu = max(1, (os.cpu_count() or 2) - 2)
    return max(1, min(by_ram, by_cpu))


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        SYNCHRONIZE = 0x00100000
        h = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not h:
            return False
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_registry() -> dict:
    try:
        with open(REGISTRY) as f:
            reg = json.load(f)
    except (OSError, ValueError):
        reg = {}
    return {pid: w for pid, w in reg.items() if _pid_alive(int(pid))}


def _write_registry(reg: dict) -> None:
    try:
        with open(REGISTRY, "w") as f:
            json.dump(reg, f)
    except OSError:
        pass


def claim_workers(requested: int | None) -> int:
    """Register this process's worker count against the machine budget and return what it
    may use: min(requested, budget minus what other live studies hold), at least 1."""
    reg = _read_registry()
    me = str(os.getpid())
    others = sum(w for pid, w in reg.items() if pid != me)
    budget = machine_budget()
    allowed = max(1, budget - others)
    workers = allowed if requested is None else max(1, min(requested, allowed))
    reg[me] = workers
    _write_registry(reg)
    return workers


def release_workers() -> None:
    reg = _read_registry()
    reg.pop(str(os.getpid()), None)
    _write_registry(reg)


def _init_worker(threads: int):
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[var] = str(threads)


def pmap(fn: Callable, items: Sequence, workers: int | None = None, blas_threads: int = 2) -> list:
    """`[fn(x) for x in items]` across processes, order preserved. `workers` is a request;
    the number actually used is capped by the machine budget net of other running studies
    (see `machine_budget`, `claim_workers`) and by the number of items."""
    items = list(items)
    if not items:
        return []
    workers = claim_workers(workers)
    workers = min(workers, len(items))
    try:
        if workers == 1:
            return [fn(x) for x in items]
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(blas_threads,)) as ex:
            return list(ex.map(fn, items))
    finally:
        release_workers()


def pstarmap(fn: Callable, arg_tuples: Iterable[tuple], workers: int | None = None, blas_threads: int = 2) -> list:
    return pmap(_Star(fn), list(arg_tuples), workers, blas_threads)


class _Star:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, args):
        return self.fn(*args)


if __name__ == "__main__":
    print(f"RAM {total_ram_bytes()/2**30:.1f} GiB, CPUs {os.cpu_count()}, budget {machine_budget()} workers, "
          f"registry {REGISTRY}: {_read_registry()}  (checked {time.strftime('%H:%M:%S')})")
