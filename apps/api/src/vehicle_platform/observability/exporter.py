"""Prevent database driver messages and SQL text from leaving the process."""

from collections.abc import Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode


class SanitizingExporter(SpanExporter):
    def __init__(self, delegate: SpanExporter) -> None:
        self.delegate = delegate

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        sanitized = []
        for span in spans:
            attributes = dict(span.attributes or {})
            database_span = "db.system" in attributes or "db.system.name" in attributes
            # Driver exceptions propagate into application parent spans too.
            # Filtering only DB spans would leak their text through those parents.
            attributes = {
                key: value for key, value in attributes.items() if not key.startswith("exception.")
            }
            attributes.pop("db.statement", None)
            attributes.pop("db.query.text", None)
            events = (
                ()
                if database_span
                else tuple(event for event in span.events if event.name != "exception")
            )
            if (
                not database_span
                and span.status.status_code is not StatusCode.ERROR
                and attributes == dict(span.attributes or {})
                and events == tuple(span.events)
            ):
                sanitized.append(span)
                continue
            sanitized.append(
                ReadableSpan(
                    name=span.name,
                    context=span.context,
                    parent=span.parent,
                    resource=span.resource,
                    attributes=attributes,
                    events=events,
                    links=span.links,
                    kind=span.kind,
                    status=Status(
                        span.status.status_code,
                        "database_error" if database_span else "operation_error",
                    )
                    if span.status.status_code is StatusCode.ERROR
                    else span.status,
                    start_time=span.start_time,
                    end_time=span.end_time,
                    instrumentation_scope=span.instrumentation_scope,
                )
            )
        return self.delegate.export(sanitized)

    def shutdown(self) -> None:
        self.delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self.delegate.force_flush(timeout_millis)
