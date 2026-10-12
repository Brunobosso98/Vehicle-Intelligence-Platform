"""Optional internal metering seam; never carries prompts, credentials or reasoning content."""

from typing import Any, Protocol


class ResponseObserver(Protocol):
    def begin(self, role: str, input_bytes: int, max_output_tokens: int) -> str: ...

    def complete(self, ticket: str, metadata: dict[str, Any]) -> None: ...

    def failed(self, ticket: str, category: str | None = None) -> None: ...
