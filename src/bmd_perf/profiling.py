import cProfile
import functools
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from pint import UnitRegistry
from viztracer import VizTracer

ureg = UnitRegistry()


def timed(func: Callable):
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter() * ureg.second
        ret_val = func(*args, **kwargs)
        t1 = time.perf_counter() * ureg.second

        dt = t1 - t0
        print(f"{func.__name__}: {dt.to_compact():~,.1f}")

        return ret_val

    return wrapper


class timed_ctx:
    def __init__(self, s: str, out: Optional[Callable] = print, verbose=True):
        self._s = s
        self._out = out
        self._verbose = verbose

    def __enter__(self):
        self._t0 = time.perf_counter() * ureg.second
        return self

    def __exit__(self, *args):
        if self._out is None or not self._verbose:
            return

        t1 = time.perf_counter() * ureg.second
        self._elapsed = t1 - self._t0

        self._out(f"{self._s}: {self._elapsed.to_compact():~,.1f}")


def viztrace(**viztracer_kwargs) -> Callable:
    def outer(func: Callable) -> Callable:
        @functools.wraps(func)
        def inner(*args, **kwargs):
            filepath = Path(sys.modules["__main__"].__file__)

            # the location for log files will most likely change; keep this for now I
            # suppose
            log_path = (
                filepath.parent
                / "logs"
                / "viztracer"
                / filepath.name
                / f"{func.__name__}_{int(time.time())}.prof"
            )
            log_path.parent.mkdir(exist_ok=True, parents=True)

            viztracer_kwargs["output_file"] = str(log_path)

            tracer = VizTracer(**viztracer_kwargs)
            tracer.start()

            try:
                ret_val = func(*args, **kwargs)
            finally:
                tracer.stop()
                tracer.save()
                tracer.terminate()

            return ret_val

        return inner

    return outer


def profile() -> Callable:
    def outer(func: Callable) -> Callable:
        @functools.wraps(func)
        def inner(*args, **kwargs):
            filepath = Path(sys.modules["__main__"].__file__)

            log_path = (
                filepath.parent
                / "logs"
                / "cprofile"
                / filepath.name
                / f"{func.__name__}_{int(time.time())}.prof"
            )

            log_path.parent.mkdir(exist_ok=True, parents=True)

            pr = cProfile.Profile()
            pr.enable()

            try:
                ret_val = func(*args, **kwargs)

            finally:
                pr.disable()
                pr.dump_stats(log_path)
                print(f"cProfile profile saved to {log_path.resolve()}")

            return ret_val

        return inner

    return outer
