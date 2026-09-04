"""Run independent study conditions in separate processes.

numpy's elementwise kernels are single-threaded, so a 16-core machine runs a sequential
study on one core. `pmap` fans conditions out to worker processes, each pinned to a
couple of BLAS threads so they do not fight over the cores. Functions and arguments
must be picklable (module-level functions; on Windows the calling script re-imports
under `__mp_main__`, so keep work out of module top level or behind `if __name__`).
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Iterable, Sequence


def _init_worker(threads: int):
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[var] = str(threads)


def pmap(fn: Callable, items: Sequence, workers: int | None = None, blas_threads: int = 2) -> list:
    """`[fn(x) for x in items]` across processes, order preserved. `workers` defaults to
    half the CPUs (each worker then gets `blas_threads` for the LU solves)."""
    items = list(items)
    if not items:
        return []
    workers = workers or max(1, (os.cpu_count() or 2) // 2)
    workers = min(workers, len(items))
    if workers == 1:
        return [fn(x) for x in items]
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(blas_threads,)) as ex:
        return list(ex.map(fn, items))


def pstarmap(fn: Callable, arg_tuples: Iterable[tuple], workers: int | None = None, blas_threads: int = 2) -> list:
    return pmap(_Star(fn), list(arg_tuples), workers, blas_threads)


class _Star:
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, args):
        return self.fn(*args)
