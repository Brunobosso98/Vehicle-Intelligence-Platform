"""Request-scoped tracing of deterministic calculations without payload attributes."""

from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from typing import ParamSpec, TypeVar

from opentelemetry.trace import Tracer

CURRENT_TRACER: ContextVar[Tracer | None] = ContextVar("analytics_tracer", default=None)
P = ParamSpec("P")
T = TypeVar("T")


def traced(name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorate(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def execute(*args: P.args, **kwargs: P.kwargs) -> T:
            tracer = CURRENT_TRACER.get()
            if tracer is None:
                return function(*args, **kwargs)
            with tracer.start_as_current_span(name):
                return function(*args, **kwargs)

        return execute

    return decorate
