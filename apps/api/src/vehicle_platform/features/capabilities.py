from collections.abc import Iterable, Mapping
from typing import Any

from vehicle_platform.features.domain import FeatureDefinition


def feature_source_capability_matrix(
    definitions: Iterable[FeatureDefinition],
    sources: Mapping[str, frozenset[str] | None],
    *,
    conditional_sources: frozenset[str] = frozenset(),
    preflight_sources: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Describe signal-set compatibility without claiming runtime availability."""
    matrix = []
    for definition in definitions:
        signals = tuple(dict.fromkeys((*definition.required_signals, *definition.optional_signals)))
        capabilities: dict[str, dict[str, Any]] = {}
        for source, supported in sorted(sources.items()):
            missing = [] if supported is None else sorted(set(signals) - supported)
            if not signals:
                status = "core"
            elif supported is None:
                status = "capability_report_required"
            elif missing:
                status = "unsupported_signal_set"
            elif source in conditional_sources:
                status = "conditional_on_input_signals"
            elif source in preflight_sources:
                status = "supported_signals_require_preflight"
            else:
                status = "supported_signal_set"
            capabilities[source] = {"status": status, "missing_signals": missing}
        matrix.append(
            {
                "key": definition.key,
                "category": definition.category.value,
                "unit": definition.unit,
                "availability": definition.availability.value,
                "required_signals": list(definition.required_signals),
                "optional_signals": list(definition.optional_signals),
                "acquisition_class": definition.acquisition_class.value,
                "minimum_quality": definition.minimum_quality,
                "nullable": definition.nullable,
                "source_capabilities": capabilities,
            }
        )
    return matrix
