import time
from typing import Callable, TypeVar

T = TypeVar("T")

HTTP_TIMEOUT_S = 120
JOB_TIMEOUT_S = 600


class ProviderTimeout(RuntimeError):
    pass


def poll_until(
    fetch: Callable[[], T],
    is_done: Callable[[T], bool],
    *,
    is_failed: Callable[[T], bool] = lambda _: False,
    timeout_s: float = JOB_TIMEOUT_S,
    interval_s: float = 1.0,
    what: str = "job",
) -> T:
    """Poll an async provider job until it finishes, fails, or times out.

    Async STT APIs (Rev.ai, Soniox) report job status by polling. An
    unbounded ``while True`` loop turns a stuck or failed job into a request
    that never returns, so every poll has a deadline and a failure check.
    """
    deadline = time.monotonic() + timeout_s
    while True:
        state = fetch()
        if is_done(state):
            return state
        if is_failed(state):
            raise RuntimeError(f"{what} failed: {state}")
        if time.monotonic() >= deadline:
            raise ProviderTimeout(f"{what} did not finish within {timeout_s:.0f}s")
        time.sleep(interval_s)
