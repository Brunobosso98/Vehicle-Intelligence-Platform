from uuid import UUID

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from vehicle_platform.mcp.adapter import Adapter
from vehicle_platform.mcp.errors import ErrorCode, PlatformError
from vehicle_platform.mcp.instrumentation import Instrumentation
from vehicle_platform.mcp.schemas import (
    Envelope,
    Limit,
    Metric,
    PullIDs,
    Samples,
    SessionIDs,
    Signals,
    Window,
)

TOOL_NAMES = frozenset(
    {
        "list_vehicles",
        "get_vehicle",
        "get_vehicle_configuration",
        "list_vehicle_modifications",
        "list_sessions",
        "get_session",
        "get_session_summary",
        "get_session_capabilities",
        "list_session_pulls",
        "get_pull",
        "get_pull_summary",
        "compare_pulls",
        "get_repeated_pull_analysis",
        "list_session_events",
        "list_pull_events",
        "get_event",
        "get_session_analytics",
        "get_vehicle_baseline",
        "get_vehicle_trend",
        "compare_configurations",
        "get_cross_session_analytics",
        "get_telemetry_window",
    }
)


def register_tools(
    server: MCPServer[None], adapter: Adapter, instrumentation: Instrumentation
) -> None:
    async def list_vehicles(limit: Limit = 20) -> Envelope:
        """List at most 100 factual vehicle records, in stable creation/ID order."""
        return adapter.envelope(await adapter.catalog.vehicles(limit + 1), {}, limit=limit)

    async def get_vehicle(vehicle_id: UUID) -> Envelope:
        """Read one vehicle's factual context by identifier."""
        return adapter.envelope(
            await adapter.entity("vehicle", vehicle_id, vehicle_id), {"vehicle_id": vehicle_id}
        )

    async def get_vehicle_configuration(vehicle_id: UUID, configuration_id: UUID) -> Envelope:
        """Read one configuration; reject a configuration belonging to another vehicle."""
        return adapter.envelope(
            await adapter.entity("configuration", configuration_id, vehicle_id),
            {"vehicle_id": vehicle_id, "configuration_id": configuration_id},
        )

    async def list_vehicle_modifications(vehicle_id: UUID, limit: Limit = 20) -> Envelope:
        """List at most 100 recorded modifications; records do not establish causal effects."""
        await adapter.entity("vehicle", vehicle_id, vehicle_id)
        return adapter.envelope(
            await adapter.catalog.modifications(vehicle_id, limit + 1),
            {"vehicle_id": vehicle_id},
            limit=limit,
        )

    async def list_sessions(
        vehicle_id: UUID, configuration_id: UUID | None = None, limit: Limit = 20
    ) -> Envelope:
        """List at most 100 sessions for one vehicle, optionally restricted to one configuration."""
        await adapter.entity("vehicle", vehicle_id, vehicle_id)
        if configuration_id:
            await adapter.entity("configuration", configuration_id, vehicle_id)
        return adapter.envelope(
            await adapter.catalog.sessions(vehicle_id, configuration_id, limit + 1),
            {"vehicle_id": vehicle_id, "configuration_id": configuration_id},
            limit=limit,
        )

    async def get_session(vehicle_id: UUID, session_id: UUID) -> Envelope:
        """Read a session record; reject cross-vehicle context. Does not return telemetry."""
        return adapter.envelope(
            await adapter.entity("session", session_id, vehicle_id),
            {"vehicle_id": vehicle_id, "session_id": session_id},
        )

    async def get_session_summary(vehicle_id: UUID, session_id: UUID) -> Envelope:
        """Get deterministic Phase 5 session summary from at most 20 pulls and 500k
        observations; no diagnosis."""
        await adapter.entity("session", session_id, vehicle_id)
        return await adapter.analytical(
            await adapter.analytics.session(session_id, adapter.config),
            {"vehicle_id": vehicle_id, "session_id": session_id},
        )

    async def get_session_capabilities(vehicle_id: UUID, session_id: UUID) -> Envelope:
        """Assess recorded signal availability with the general-health recipe; missing signals
        are explicit."""
        await adapter.entity("session", session_id, vehicle_id)
        return adapter.envelope(
            await adapter.acquisition.capability_report(
                session_id, "general-health", persist=False
            ),
            {"vehicle_id": vehicle_id, "session_id": session_id},
        )

    async def list_session_pulls(vehicle_id: UUID, session_id: UUID, limit: Limit = 20) -> Envelope:
        """List at most 100 existing factual pulls in chronological/ID order; never reruns
        detection."""
        await adapter.entity("session", session_id, vehicle_id)
        data = await adapter.analysis.pulls(session_id, vehicle_id, limit + 1)
        return adapter.envelope(
            [item.model_dump(mode="json") for item in data],
            {"vehicle_id": vehicle_id, "session_id": session_id},
            limit=limit,
        )

    async def get_pull(vehicle_id: UUID, pull_id: UUID) -> Envelope:
        """Read one detected pull with boundaries, detector identity and provenance."""
        return adapter.envelope(
            await adapter.pull(vehicle_id, pull_id), {"vehicle_id": vehicle_id, "pull_id": pull_id}
        )

    async def get_pull_summary(vehicle_id: UUID, pull_id: UUID) -> Envelope:
        """Calculate deterministic Phase 5 pull profile, bounded to 500k observations, without
        persisting a run."""
        await adapter.pull(vehicle_id, pull_id)
        return await adapter.analytical(
            await adapter.analytics.pull(pull_id, adapter.config),
            {"vehicle_id": vehicle_id, "pull_id": pull_id},
        )

    async def compare_pulls(vehicle_id: UUID, pull_ids: PullIDs) -> Envelope:
        """Compare 2–20 unique pulls from the same vehicle/configuration using Phase 5
        comparability rules."""
        await adapter.selected_pulls(vehicle_id, pull_ids)
        return await adapter.analytical(
            await adapter.analytics.comparison(pull_ids, adapter.config),
            {"vehicle_id": vehicle_id, "pull_ids": pull_ids},
        )

    async def get_repeated_pull_analysis(vehicle_id: UUID, pull_ids: PullIDs) -> Envelope:
        """Analyze 2–20 repeated pulls from one vehicle/configuration; report observed
        associations only."""
        await adapter.selected_pulls(vehicle_id, pull_ids)
        return await adapter.analytical(
            await adapter.analytics.repeated(pull_ids, adapter.config),
            {"vehicle_id": vehicle_id, "pull_ids": pull_ids},
        )

    async def list_session_events(
        vehicle_id: UUID, session_id: UUID, limit: Limit = 20
    ) -> Envelope:
        """List at most 100 factual session events with evidence and detector versions; events
        are not diagnosis."""
        await adapter.entity("session", session_id, vehicle_id)
        data = await adapter.events.events(
            session_id, vehicle_id, None, None, None, None, None, None, limit + 1
        )
        return adapter.envelope(
            [item.model_dump(mode="json") for item in data],
            {"vehicle_id": vehicle_id, "session_id": session_id},
            limit=limit,
        )

    async def list_pull_events(vehicle_id: UUID, pull_id: UUID, limit: Limit = 20) -> Envelope:
        """List at most 100 factual events associated with one validated pull; no causal
        inference."""
        await adapter.pull(vehicle_id, pull_id)
        data = await adapter.events.events(
            None, vehicle_id, None, None, None, pull_id, None, None, limit + 1
        )
        return adapter.envelope(
            [item.model_dump(mode="json") for item in data],
            {"vehicle_id": vehicle_id, "pull_id": pull_id},
            limit=limit,
        )

    async def get_event(vehicle_id: UUID, event_id: UUID) -> Envelope:
        """Read one factual event, including boundaries, evidence, source IDs and detector
        identity."""
        event = await adapter.events.event(event_id)
        if event is None:
            raise PlatformError(ErrorCode.NOT_FOUND)
        if event.vehicle_id != vehicle_id:
            raise PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT)
        return adapter.envelope(
            event.model_dump(mode="json"), {"vehicle_id": vehicle_id, "event_id": event_id}
        )

    async def get_session_analytics(vehicle_id: UUID, session_id: UUID) -> Envelope:
        """Read deterministic session analytics (20 pulls/500k observations maximum) without
        changing stored results."""
        return await get_session_summary(vehicle_id, session_id)

    async def get_vehicle_baseline(vehicle_id: UUID, configuration_id: UUID) -> Envelope:
        """Calculate a configuration-isolated baseline from at most 20 historical pulls; report
        insufficient history explicitly."""
        await adapter.entity("configuration", configuration_id, vehicle_id)
        return await adapter.analytical(
            await adapter.analytics.vehicle_baseline(vehicle_id, configuration_id, adapter.config),
            {"vehicle_id": vehicle_id, "configuration_id": configuration_id},
        )

    async def get_vehicle_trend(vehicle_id: UUID, metric: Metric) -> Envelope:
        """Calculate one of seven Phase 5 metrics over at most 20 pulls, segmented by
        configuration; association only."""
        await adapter.entity("vehicle", vehicle_id, vehicle_id)
        return await adapter.analytical(
            await adapter.analytics.trends(vehicle_id, metric, adapter.config),
            {"vehicle_id": vehicle_id},
        )

    async def compare_configurations(
        vehicle_id: UUID, before_pull_ids: PullIDs, after_pull_ids: PullIDs
    ) -> Envelope:
        """Compare two distinct configurations of one vehicle using 4–20 total unique pulls,
        at least two per configuration;
        observed differences never establish causation."""
        if len(before_pull_ids + after_pull_ids) > 20:
            raise PlatformError(ErrorCode.INVALID_ARGUMENT)
        before = await adapter.selected_pulls(vehicle_id, before_pull_ids)
        after = await adapter.selected_pulls(vehicle_id, after_pull_ids)
        await adapter.selected_pulls(
            vehicle_id, before_pull_ids + after_pull_ids, same_configuration=False
        )
        if before[0]["configuration_id"] == after[0]["configuration_id"]:
            raise PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT)
        return await adapter.analytical(
            await adapter.analytics.modifications(before_pull_ids, after_pull_ids, adapter.config),
            {"vehicle_id": vehicle_id, "pull_ids": before_pull_ids + after_pull_ids},
        )

    async def get_cross_session_analytics(vehicle_id: UUID, session_ids: SessionIDs) -> Envelope:
        """Compare 2–10 unique sessions of one vehicle/configuration, selecting at most 20 pulls."""
        if len(set(session_ids)) != len(session_ids):
            raise PlatformError(ErrorCode.INVALID_ARGUMENT)
        sessions = [await adapter.entity("session", item, vehicle_id) for item in session_ids]
        if len({item["configuration_id"] for item in sessions}) != 1:
            raise PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT)
        return await adapter.analytical(
            await adapter.analytics.cross_sessions(session_ids, adapter.config),
            {"vehicle_id": vehicle_id, "session_ids": session_ids},
        )

    async def get_telemetry_window(
        vehicle_id: UUID,
        session_id: UUID,
        signals: Signals,
        window: Window,
        max_samples: Samples = 500,
    ) -> Envelope:
        """Read 1–8 explicit canonical signals for an aware time window of at most 60s, at most
        1000 samples; preserves units and identity."""
        return await adapter.window(vehicle_id, session_id, signals, window, max_samples)

    annotations = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
    )
    for function in (
        list_vehicles,
        get_vehicle,
        get_vehicle_configuration,
        list_vehicle_modifications,
        list_sessions,
        get_session,
        get_session_summary,
        get_session_capabilities,
        list_session_pulls,
        get_pull,
        get_pull_summary,
        compare_pulls,
        get_repeated_pull_analysis,
        list_session_events,
        list_pull_events,
        get_event,
        get_session_analytics,
        get_vehicle_baseline,
        get_vehicle_trend,
        compare_configurations,
        get_cross_session_analytics,
        get_telemetry_window,
    ):
        server.add_tool(instrumentation.wrap(function), annotations=annotations)
