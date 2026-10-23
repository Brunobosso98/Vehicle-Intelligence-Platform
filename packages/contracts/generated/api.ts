export interface paths {
  "/api/v1/acquisitions": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Create Acquisition */
    post: operations["create_acquisition"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/acquisitions/{acquisition_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Acquisition */
    get: operations["get_acquisition"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/acquisitions/{acquisition_id}/batches": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Publish Acquisition Batch */
    post: operations["publish_acquisition_batch"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/acquisitions/{acquisition_id}/finalize": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Finalize Acquisition */
    post: operations["finalize_acquisition"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/acquisitions/{acquisition_id}/findings": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Acquisition Findings */
    get: operations["list_acquisition_findings"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/acquisitions/{acquisition_id}/heartbeat": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Report Acquisition Heartbeat */
    post: operations["report_acquisition_heartbeat"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/acquisitions/{acquisition_id}/live": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Stream Acquisition Live */
    get: operations["stream_acquisition_live"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/acquisitions/{acquisition_id}/stop": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Stop Acquisition */
    post: operations["stop_acquisition"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/acquisitions/{acquisition_id}/synthetic": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Start Synthetic Acquisition */
    post: operations["start_synthetic_acquisition"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/analytics/configurations/compare": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Compare Configurations */
    post: operations["compare_configurations"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/analytics/pulls/compare": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Compare Pull Analytics */
    post: operations["compare_pull_analytics"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/analytics/pulls/repeated": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Analyze Repeated Pulls */
    post: operations["analyze_repeated_pulls"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/analytics/sessions/compare": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Compare Sessions */
    post: operations["compare_sessions"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/events": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Vehicle Events */
    get: operations["list_vehicle_events"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/events/{event_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Event */
    get: operations["get_event"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/knowledge": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Catalog */
    get: operations["catalog_api_v1_knowledge_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/logging/objectives": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Logging Objectives */
    get: operations["list_logging_objectives"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/logging/recipes": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Logging Recipes */
    get: operations["list_logging_recipes"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/logging/recipes/{recipe_key}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Logging Recipe */
    get: operations["get_logging_recipe"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/logging/recipes/{recipe_key}/preflight": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Preflight Logging Recipe */
    post: operations["preflight_logging_recipe"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/prediction-service/anomalies": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Anomalies */
    post: operations["prediction_service_anomalies"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/prediction-service/evidence/{evidence_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Evidence */
    get: operations["prediction_service_evidence"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/prediction-service/evidence/{evidence_id}/verify": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Verify Evidence */
    post: operations["prediction_service_verify_evidence"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/prediction-service/next-pull": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Next Pull */
    post: operations["prediction_service_next_pull"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/prediction-service/runs/{receipt_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Receipt */
    get: operations["prediction_service_receipt"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/prediction-service/runs/{receipt_id}/evidence": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Receipt Evidence */
    get: operations["prediction_service_receipt_evidence"];
    put?: never;
    /** Materialize Evidence */
    post: operations["prediction_service_materialize_evidence"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/prediction-service/versions": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Versions */
    get: operations["prediction_service_versions"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/pulls": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Pulls */
    get: operations["list_pulls"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/pulls/{pull_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Pull */
    get: operations["get_pull"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/pulls/{pull_id}/analytics": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Get Pull Analytics */
    post: operations["get_pull_analytics"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Sessions */
    get: operations["list_sessions"];
    put?: never;
    /** Create Session */
    post: operations["create_session"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Session */
    get: operations["get_session"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/analysis": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Analyze Session */
    post: operations["analyze_session"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/analytics": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Get Session Analytics */
    post: operations["get_session_analytics"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/capabilities": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Assess Session Capabilities */
    get: operations["assess_session_capabilities"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/events": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Session Events */
    get: operations["list_session_events"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/events/analyze": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Analyze Session Events */
    post: operations["analyze_session_events"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/events/summary": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Summarize Session Events */
    get: operations["summarize_session_events"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/imports/csv": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Import Csv */
    post: operations["import_csv"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/imports/csv/preview": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Preview Csv Import */
    post: operations["preview_csv_import"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/pulls": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Session Pulls */
    get: operations["list_session_pulls"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/segments": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Session Segments */
    get: operations["list_session_segments"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/sessions/{session_id}/telemetry": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Query Telemetry */
    get: operations["query_telemetry"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/signals": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Signals */
    get: operations["list_signals"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Vehicles */
    get: operations["list_vehicles"];
    put?: never;
    /** Create Vehicle */
    post: operations["create_vehicle"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Vehicle */
    get: operations["get_vehicle"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Update Vehicle */
    patch: operations["update_vehicle"];
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/agent-runs": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Recent */
    get: operations["recent_api_v1_vehicles__vehicle_id__agent_runs_get"];
    put?: never;
    /** Ask */
    post: operations["ask_api_v1_vehicles__vehicle_id__agent_runs_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/agent-runs/{run_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get */
    get: operations["get_api_v1_vehicles__vehicle_id__agent_runs__run_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/agent-runs/{run_id}/audit": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Audit */
    get: operations["audit_api_v1_vehicles__vehicle_id__agent_runs__run_id__audit_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/agent-runs/{run_id}/cancel": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cancel */
    post: operations["cancel_api_v1_vehicles__vehicle_id__agent_runs__run_id__cancel_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/agent-runs/{run_id}/events": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Events */
    get: operations["events_api_v1_vehicles__vehicle_id__agent_runs__run_id__events_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/agent-runs/{run_id}/stream": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Stream */
    get: operations["stream_api_v1_vehicles__vehicle_id__agent_runs__run_id__stream_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/configurations": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Configurations */
    get: operations["list_configurations"];
    put?: never;
    /** Create Configuration */
    post: operations["create_configuration"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/configurations/{configuration_id}/baseline": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Build Vehicle Baseline */
    post: operations["build_vehicle_baseline"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Recent */
    get: operations["recent_api_v1_vehicles__vehicle_id__investigations_get"];
    put?: never;
    /** Create */
    post: operations["create_api_v1_vehicles__vehicle_id__investigations_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/source-preflight": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Source Preflight */
    post: operations["source_preflight_api_v1_vehicles__vehicle_id__investigations_source_preflight_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/{investigation_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get */
    get: operations["get_api_v1_vehicles__vehicle_id__investigations__investigation_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/{investigation_id}/approve": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Approve */
    post: operations["approve_api_v1_vehicles__vehicle_id__investigations__investigation_id__approve_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/{investigation_id}/cancel": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cancel */
    post: operations["cancel_api_v1_vehicles__vehicle_id__investigations__investigation_id__cancel_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/{investigation_id}/events": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Events */
    get: operations["events_api_v1_vehicles__vehicle_id__investigations__investigation_id__events_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/{investigation_id}/reanalyze": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Reanalyze */
    post: operations["reanalyze_api_v1_vehicles__vehicle_id__investigations__investigation_id__reanalyze_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/{investigation_id}/refresh": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Refresh */
    post: operations["refresh_api_v1_vehicles__vehicle_id__investigations__investigation_id__refresh_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/{investigation_id}/reject": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Reject */
    post: operations["reject_api_v1_vehicles__vehicle_id__investigations__investigation_id__reject_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/{investigation_id}/sessions": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Link Session */
    post: operations["link_session_api_v1_vehicles__vehicle_id__investigations__investigation_id__sessions_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/investigations/{investigation_id}/stream": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Stream */
    get: operations["stream_api_v1_vehicles__vehicle_id__investigations__investigation_id__stream_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/knowledge/query": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Search */
    post: operations["search_api_v1_vehicles__vehicle_id__knowledge_query_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/knowledge/retrievals/{retrieval_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Retrieval */
    get: operations["retrieval_api_v1_vehicles__vehicle_id__knowledge_retrievals__retrieval_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/modifications": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Modifications */
    get: operations["list_modifications"];
    put?: never;
    /** Create Modification */
    post: operations["create_modification"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/vehicles/{vehicle_id}/trends/{metric}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Get Vehicle Trends */
    post: operations["get_vehicle_trends"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/health/live": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Live */
    get: operations["health_live"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/health/ready": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Ready */
    get: operations["health_ready"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/version": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Version */
    get: operations["version"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    /** AcquisitionBatch */
    AcquisitionBatch: {
      /**
       * Batch Id
       * Format: uuid
       */
      batch_id: string;
      /** Observations */
      observations: components["schemas"]["StreamObservation"][];
      /**
       * Schema Version
       * @constant
       */
      schema_version: "1.0";
    };
    /** AcquisitionBatchAccepted */
    AcquisitionBatchAccepted: {
      /** Accepted */
      accepted: number;
      /**
       * Batch Id
       * Format: uuid
       */
      batch_id: string;
      /**
       * Topic
       * @default telemetry.raw.v1
       */
      topic: string;
    };
    /** AcquisitionCreate */
    AcquisitionCreate: {
      /**
       * Adapter
       * @enum {string}
       */
      adapter: "synthetic" | "replay" | "obd";
      /** Configuration Id */
      configuration_id?: string | null;
      /** Recipe Key */
      recipe_key: string;
      /** Source Id */
      source_id: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** AcquisitionCreated */
    AcquisitionCreated: {
      /**
       * Driving Session Id
       * Format: uuid
       */
      driving_session_id: string;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Ingestion Token */
      ingestion_token: string;
      /** State */
      state: string;
      /**
       * Token Expires At
       * Format: date-time
       */
      token_expires_at: string;
    };
    /** AcquisitionFinalized */
    AcquisitionFinalized: {
      capability_report: components["schemas"]["DatasetCapabilityReport"];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      phase2: components["schemas"]["AnalysisResult"];
      phase3: components["schemas"]["EventAnalysisResult"];
      /** Reconciliation */
      reconciliation: {
        [key: string]: number;
      };
      /**
       * State
       * @constant
       */
      state: "completed";
    };
    /** AcquisitionHeartbeat */
    AcquisitionHeartbeat: {
      /**
       * Adapter State
       * @enum {string}
       */
      adapter_state: "connected" | "disconnected";
      capability_snapshot?: components["schemas"]["PreflightRequest"] | null;
      /**
       * Collection Started At
       * Format: date-time
       */
      collection_started_at: string;
      /** Dropped Observations */
      dropped_observations: number;
      /** Last Sample Received At */
      last_sample_received_at?: string | null;
      /** Queue Observations */
      queue_observations: number;
      /** Sampling Plan */
      sampling_plan?: components["schemas"]["SamplingPlanResponse"][];
      /** Spool Bytes */
      spool_bytes: number;
      /** Spool Capacity Bytes */
      spool_capacity_bytes?: number | null;
      /** Spool Capacity State */
      spool_capacity_state?:
        ("normal" | "warning" | "near_capacity" | "capacity_reached") | null;
    };
    /** AcquisitionLiveQuality */
    AcquisitionLiveQuality: {
      collector?: components["schemas"]["CollectorReportedState"] | null;
      collector_health: components["schemas"]["CollectorHealthResponse"];
      pipeline?: components["schemas"]["AcquisitionPipelineMeasurement"] | null;
      /** Signals */
      signals?: components["schemas"]["LiveSignalQuality"][];
    } & {
      [key: string]: unknown;
    };
    /** AcquisitionLiveSnapshot */
    AcquisitionLiveSnapshot: {
      /** Findings */
      findings: components["schemas"]["ProvisionalFindingResponse"][];
      /** Points */
      points: components["schemas"]["LiveTelemetryPoint"][];
      /**
       * Provisional
       * @default true
       * @constant
       */
      provisional: true;
      quality: components["schemas"]["AcquisitionLiveQuality"];
      /**
       * Schema Version
       * @default 1.0
       * @constant
       */
      schema_version: "1.0";
      /** State */
      state: string;
      /**
       * Window Seconds
       * @default 60
       * @constant
       */
      window_seconds: 60;
    };
    /** AcquisitionPipelineMeasurement */
    AcquisitionPipelineMeasurement: {
      /** Broker Consumer Lag */
      broker_consumer_lag?: number | null;
      /**
       * Measured At
       * Format: date-time
       */
      measured_at: string;
      /**
       * Persistence State
       * @constant
       */
      persistence_state: "observations_committed";
      /** Publisher To Persistence Seconds */
      publisher_to_persistence_seconds?: number | null;
    };
    /** AcquisitionStatusResponse */
    AcquisitionStatusResponse: {
      /** Adapter */
      adapter: string;
      /**
       * Driving Session Id
       * Format: uuid
       */
      driving_session_id: string;
      /** Ended At */
      ended_at: string | null;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Quality */
      quality: {
        [key: string]: unknown;
      };
      /** Recipe Key */
      recipe_key: string;
      /** Recipe Version */
      recipe_version: number;
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      /** State */
      state: string;
    };
    /** AgentRun */
    AgentRun: {
      /** Agent Version */
      agent_version: string;
      /** Completed At */
      completed_at?: string | null;
      /** Duration Seconds */
      duration_seconds?: number | null;
      /** Error Category */
      error_category?: string | null;
      /** Evidence */
      evidence?: components["schemas"]["Evidence"][];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Model */
      model: string;
      /** Prompt Version */
      prompt_version: string;
      /** Provider */
      provider: string;
      result?: components["schemas"]["Answer"] | null;
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      /**
       * Status
       * @enum {string}
       */
      status: "running" | "completed" | "failed" | "cancelled";
      supervisor?: components["schemas"]["SupervisorReport"] | null;
      /**
       * Tool Call Count
       * @default 0
       */
      tool_call_count: number;
      /** Trace Id */
      trace_id?: string | null;
      usage?: components["schemas"]["Usage"];
      /** User Question */
      user_question: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** AnalysisRequest */
    AnalysisRequest: {
      /**
       * Profile
       * @default generic-v1
       * @enum {string}
       */
      profile: "generic-v1" | "bmw-f30-n55-heuristic-v1";
      /**
       * Replace
       * @default false
       */
      replace: boolean;
    };
    /** AnalysisResult */
    AnalysisResult: {
      /** Algorithm Version */
      algorithm_version: string;
      /** Configuration Hash */
      configuration_hash: string;
      /** Profile */
      profile: string;
      /** Pull Count */
      pull_count: number;
      /** Reused */
      reused: boolean;
      /** Segment Count */
      segment_count: number;
      /**
       * Session Id
       * Format: uuid
       */
      session_id: string;
    };
    /** AnalyticsRequest */
    AnalyticsRequest: {
      /**
       * Maximum Gap Seconds
       * @default 1
       */
      maximum_gap_seconds: number;
      /**
       * Minimum Bin Samples
       * @default 3
       */
      minimum_bin_samples: number;
      /** Pull Ids */
      pull_ids?: string[];
      /**
       * Recompute
       * @default false
       */
      recompute: boolean;
      /**
       * Rpm Bin Size
       * @default 250
       */
      rpm_bin_size: number;
      /** Speed Intervals Kmh */
      speed_intervals_kmh?: [number, number][];
    };
    /** AnalyticsResultResponse */
    AnalyticsResultResponse: {
      /** Algorithm Name */
      algorithm_name: string;
      /** Algorithm Version */
      algorithm_version: string;
      /** Analytics Type */
      analytics_type: string;
      /** Configuration Hash */
      configuration_hash: string;
      /** Configuration Id */
      configuration_id: string | null;
      /**
       * Generated At
       * Format: date-time
       */
      generated_at: string;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Result */
      result: {
        [key: string]: unknown;
      };
      /**
       * Reused
       * @default false
       */
      reused: boolean;
      /** Source Fingerprint */
      source_fingerprint: string;
      /**
       * Status
       * @enum {string}
       */
      status: "completed" | "limited" | "insufficient" | "failed";
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /** Warnings */
      warnings: string[];
    };
    /** AnomalyRequest */
    AnomalyRequest: {
      /** Detector Version Id */
      detector_version_id?: string | null;
      /**
       * Family
       * @enum {string}
       */
      family: "thermal" | "boost_air" | "performance" | "fuel";
      /**
       * Observation Cutoff
       * Format: date-time
       */
      observation_cutoff: string;
      /**
       * Pull Id
       * Format: uuid
       */
      pull_id: string;
      source_role: components["schemas"]["SourceRole"];
      /** Vehicle Id */
      vehicle_id?: string | null;
    };
    /** Answer */
    Answer: {
      /** Answer */
      answer: string;
      /**
       * Confidence
       * @enum {string}
       */
      confidence: "low" | "moderate" | "high";
      context: components["schemas"]["VehicleContext"];
      /** Evidence */
      evidence: components["schemas"]["Evidence"][];
      /** Findings */
      findings: components["schemas"]["Finding"][];
      knowledge?: components["schemas"]["KnowledgeReport"] | null;
      /** Limitations */
      limitations: string[];
      /** Missing Evidence */
      missing_evidence: string[];
      /**
       * Schema Version
       * @default 1.0
       * @constant
       */
      schema_version: "1.0";
      /** Uncertainties */
      uncertainties: string[];
    };
    /** Applicability */
    Applicability: {
      /**
       * Calibration
       * @default principle
       * @enum {string}
       */
      calibration: "principle" | "stock" | "tune_specific";
      /** Component */
      component?: string | null;
      /** Effective From */
      effective_from?: string | null;
      /** Effective To */
      effective_to?: string | null;
      /** Engine */
      engine?: string | null;
      /** Engine Variant */
      engine_variant?: string | null;
      /** Fuel */
      fuel?: string | null;
      /** Hardware */
      hardware?: string[];
      /** Make */
      make?: string | null;
      /** Map Version */
      map_version?: string | null;
      /** Model */
      model?: string | null;
      /** Part Number */
      part_number?: string | null;
      /** Platform */
      platform?: string | null;
      /** Region */
      region?: string | null;
      /** Stage */
      stage?: string | null;
      /** Subsystems */
      subsystems?: string[];
      /** Transmission */
      transmission?: string | null;
      /** Tuner */
      tuner?: string | null;
      /** Year From */
      year_from?: number | null;
      /** Year To */
      year_to?: number | null;
    };
    /** Approval */
    Approval: {
      /** Actor */
      actor?: string | null;
      /** Approved At */
      approved_at?: string | null;
      /** Recipe Hash */
      recipe_hash?: string | null;
      /**
       * Status
       * @default PENDING
       */
      status: string;
    };
    /** ApprovalRequest */
    ApprovalRequest: {
      /** Recipe Hash */
      recipe_hash: string;
      /** Version */
      version: number;
    };
    /**
     * ArtifactAvailability
     * @enum {string}
     */
    ArtifactAvailability:
      "VERIFIED" | "NOT_APPLICABLE" | "UNAVAILABLE" | "CHECKSUM_MISMATCH";
    /** Ask */
    Ask: {
      /**
       * Include Prediction Evidence
       * @default false
       */
      include_prediction_evidence: boolean;
      /** Prediction Evidence Ids */
      prediction_evidence_ids?: string[];
      /** Previous Run Id */
      previous_run_id?: string | null;
      /** Pull Id */
      pull_id?: string | null;
      /** Question */
      question: string;
      /** Session Id */
      session_id?: string | null;
    };
    /**
     * Availability
     * @enum {string}
     */
    Availability:
      | "AVAILABLE"
      | "AVAILABLE_DEGRADED"
      | "UNAVAILABLE"
      | "UNKNOWN"
      | "NOT_APPLICABLE";
    /** Binding */
    Binding: {
      /**
       * Evidence Id
       * Format: uuid
       */
      evidence_id: string;
      /** Path */
      path: string;
      /** Unit */
      unit?: string | null;
      /** Value */
      value: string | number | boolean | null;
    };
    /** Body_import_csv */
    Body_import_csv: {
      /** File */
      file: string;
      /** Mapping */
      mapping?: string | null;
    };
    /** Body_preview_csv_import */
    Body_preview_csv_import: {
      /** File */
      file: string;
      /** Mapping */
      mapping?: string | null;
    };
    /** CSVColumnMapping */
    CSVColumnMapping: {
      /** Record Id Column */
      record_id_column?: string | null;
      /** Sequence Column */
      sequence_column?: string | null;
      /** Signals */
      signals: components["schemas"]["CSVSignalColumn"][];
      /** Timestamp Column */
      timestamp_column: string;
    };
    /** CSVImportPreview */
    CSVImportPreview: {
      /** Columns */
      columns: string[];
      mapping?: components["schemas"]["CSVColumnMapping"] | null;
      /** Mapping Hash */
      mapping_hash?: string | null;
      /** Preview Points */
      preview_points?: components["schemas"]["CSVPreviewPoint"][];
      /**
       * Preview Truncated
       * @default false
       */
      preview_truncated: boolean;
      /** Requires Mapping */
      requires_mapping: boolean;
      /**
       * Schema Version
       * @default 1.0
       * @constant
       */
      schema_version: "1.0";
      /** Unmapped Columns */
      unmapped_columns: string[];
      /**
       * Validation Scope
       * @default preview only; full records and context validated during import
       */
      validation_scope: string;
      /** Warnings */
      warnings?: string[];
    };
    /** CSVPreviewPoint */
    CSVPreviewPoint: {
      /**
       * Observed At
       * Format: date-time
       */
      observed_at: string;
      /** Quality */
      quality: string;
      /** Raw Signal */
      raw_signal: string;
      /** Signal */
      signal: string;
      /** Unit */
      unit: string;
      /** Value */
      value: number;
    };
    /** CSVSignalColumn */
    CSVSignalColumn: {
      /** Column */
      column: string;
      /** Signal */
      signal: string;
      /** Unit */
      unit: string;
    };
    /** CapabilitySnapshot */
    CapabilitySnapshot: {
      /** Adapter */
      adapter: string;
      /** Maximum Requests Per Second */
      maximum_requests_per_second: number;
      /**
       * Observed At
       * Format: date-time
       */
      observed_at: string;
      /** Signals */
      signals: {
        [key: string]: components["schemas"]["Support"];
      };
      /** Source Acquisition Id */
      source_acquisition_id?: string | null;
      /** Source Preflight Id */
      source_preflight_id?: string | null;
    };
    /**
     * Classification
     * @enum {string}
     */
    Classification:
      | "OBSERVATION"
      | "ASSOCIATION"
      | "HYPOTHESIS"
      | "SUPPORTED_CONCLUSION"
      | "MODEL_CLASSIFICATION"
      | "STATISTICAL_OUTLIER"
      | "DESCRIPTIVE_ASSOCIATION"
      | "DATA_GAP"
      | "DOCUMENTARY_REFERENCE"
      | "UNKNOWN"
      | "INSUFFICIENT_EVIDENCE";
    /** CollectorHealthResponse */
    CollectorHealthResponse: {
      /** Heartbeat Age Seconds */
      heartbeat_age_seconds: number | null;
      /** Sample Receipt Age Seconds */
      sample_receipt_age_seconds?: number | null;
      /**
       * State
       * @enum {string}
       */
      state:
        "not_reported" | "silent" | "disconnected" | "stalled" | "connected";
    };
    /** CollectorReportedState */
    CollectorReportedState: {
      /**
       * Adapter State
       * @enum {string}
       */
      adapter_state: "connected" | "disconnected";
      capability_snapshot?: components["schemas"]["PreflightRequest"] | null;
      /**
       * Collection Started At
       * Format: date-time
       */
      collection_started_at: string;
      /** Dropped Observations */
      dropped_observations: number;
      /** Last Sample Received At */
      last_sample_received_at?: string | null;
      /** Queue Observations */
      queue_observations: number;
      /**
       * Received At
       * Format: date-time
       */
      received_at: string;
      /** Sampling Plan */
      sampling_plan?: components["schemas"]["SamplingPlanResponse"][];
      /** Spool Bytes */
      spool_bytes: number;
      /** Spool Capacity Bytes */
      spool_capacity_bytes?: number | null;
      /** Spool Capacity State */
      spool_capacity_state?:
        ("normal" | "warning" | "near_capacity" | "capacity_reached") | null;
    };
    /** ConfigurationCreate */
    ConfigurationCreate: {
      /** Description */
      description: string;
      /**
       * Effective At
       * Format: date-time
       */
      effective_at: string;
      /** Ended At */
      ended_at?: string | null;
      /** Metadata */
      metadata?: {
        [key: string]: unknown;
      };
      /** Provenance */
      provenance: string;
    };
    /** Conflict */
    Conflict: {
      /**
       * Conflict Id
       * Format: uuid
       */
      conflict_id: string;
      /** Explanation */
      explanation: string;
      /** Finding Ids */
      finding_ids: string[];
      /** Requires Investigation */
      requires_investigation: boolean;
      /** Resolvable With Existing Evidence */
      resolvable_with_existing_evidence: boolean;
      /**
       * Severity
       * @enum {string}
       */
      severity: "warning" | "critical";
      /**
       * Type
       * @enum {string}
       */
      type:
        "factual" | "temporal_scope" | "sufficiency" | "competing_hypotheses";
    };
    /** CreateInvestigation */
    CreateInvestigation: {
      /**
       * Adapter
       * @enum {string}
       */
      adapter: "synthetic" | "replay" | "obd";
      /**
       * Agent Run Id
       * Format: uuid
       */
      agent_run_id: string;
      /** Source Id */
      source_id: string;
    };
    /** DatasetCapabilityReport */
    DatasetCapabilityReport: {
      /**
       * Assessment Version
       * @constant
       */
      assessment_version: "1.1.0";
      /** Available Signals */
      available_signals: string[];
      /** Capabilities */
      capabilities: components["schemas"]["DatasetCapabilityResponse"][];
      /** Duration Seconds */
      duration_seconds: number;
      /** Gaps By Signal */
      gaps_by_signal: {
        [key: string]: components["schemas"]["DatasetSignalGap"];
      };
      /** Observation Count */
      observation_count: number;
      /** Recipe Adherence */
      recipe_adherence: boolean;
      /** Recipe Configuration Hash */
      recipe_configuration_hash: string;
      /** Signal Quality */
      signal_quality: components["schemas"]["LiveSignalQuality"][];
    };
    /** DatasetCapabilityResponse */
    DatasetCapabilityResponse: {
      /** Evidence */
      evidence: string[];
      /** Key */
      key: string;
      /** Supported */
      supported: boolean;
      /** Unavailable Reason */
      unavailable_reason?: string | null;
    };
    /** DatasetSignalGap */
    DatasetSignalGap: {
      /** Count */
      count: number;
      /** Maximum Seconds */
      maximum_seconds: number;
    };
    /** DetectedEvent */
    DetectedEvent: {
      /** Algorithm Name */
      algorithm_name: string;
      /** Algorithm Version */
      algorithm_version: string;
      /**
       * Analysis Run Id
       * Format: uuid
       */
      analysis_run_id: string;
      /** Baseline Reference */
      baseline_reference: {
        [key: string]: unknown;
      };
      /**
       * Baseline Type
       * @enum {string}
       */
      baseline_type:
        | "same_session_pulls"
        | "vehicle_configuration_history"
        | "profile_threshold"
        | "absolute_threshold"
        | "no_baseline";
      /**
       * Category
       * @enum {string}
       */
      category:
        | "performance"
        | "thermal"
        | "fuel"
        | "ignition"
        | "combustion"
        | "mixture"
        | "sensor"
        | "telemetry_quality"
        | "control_behavior";
      /** Confidence */
      confidence: number;
      /** Configuration Hash */
      configuration_hash: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Duration Ms */
      duration_ms: number;
      /**
       * Ended At
       * Format: date-time
       */
      ended_at: string;
      /** Event Type */
      event_type: string;
      /** Evidence */
      evidence: {
        [key: string]: unknown;
      };
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Pull Id */
      pull_id: string | null;
      /** Quality Flags */
      quality_flags: string[];
      /** Segment Id */
      segment_id: string | null;
      /**
       * Session Id
       * Format: uuid
       */
      session_id: string;
      /**
       * Severity
       * @enum {string}
       */
      severity: "info" | "low" | "moderate" | "high";
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** DocumentVersion */
    DocumentVersion: {
      applicability: components["schemas"]["Applicability"];
      /** Checksum */
      checksum: string;
      /**
       * Document Id
       * Format: uuid
       */
      document_id: string;
      /**
       * Extraction Version
       * @default selection-v1
       */
      extraction_version: string;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /**
       * Language
       * @default en
       */
      language: string;
      /** License Note */
      license_note: string;
      /** Limitations */
      limitations?: string[];
      /**
       * Mime
       * @enum {string}
       */
      mime: "application/pdf" | "text/html" | "text/plain" | "text/markdown";
      /** Publication Date */
      publication_date?: string | null;
      /**
       * Redistribution
       * @default metadata_only
       * @enum {string}
       */
      redistribution: "metadata_only" | "permitted" | "synthetic";
      /**
       * Retrieved At
       * Format: date-time
       */
      retrieved_at: string;
      /** Source Checksum */
      source_checksum?: string | null;
      /**
       * Source Id
       * Format: uuid
       */
      source_id: string;
      /** Source Version */
      source_version: number;
      /**
       * Status
       * @default PENDING
       * @enum {string}
       */
      status: "PENDING" | "EXTRACTED" | "INDEXED" | "FAILED" | "QUARANTINED";
      /** Title */
      title: string;
      /** Version Label */
      version_label?: string | null;
    };
    /** DrivingSession */
    DrivingSession: {
      /** Configuration Id */
      configuration_id?: string | null;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Ended At */
      ended_at?: string | null;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Metadata */
      metadata?: {
        [key: string]: unknown;
      };
      /** Sample Count */
      sample_count: number;
      /** Source Reference */
      source_reference?: string | null;
      /** Source Timezone */
      source_timezone?: string | null;
      /**
       * Source Type
       * @enum {string}
       */
      source_type: "csv" | "synthetic" | "obd";
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      /**
       * Status
       * @enum {string}
       */
      status: "pending" | "ingesting" | "completed" | "failed";
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** ErrorDetail */
    ErrorDetail: {
      /** Code */
      code: string;
      /** Message */
      message: string;
      /** Request Id */
      request_id: string;
    };
    /** ErrorResponse */
    ErrorResponse: {
      error: components["schemas"]["ErrorDetail"];
    };
    /** EventAnalysisRequest */
    EventAnalysisRequest: {
      /**
       * Replace
       * @default false
       */
      replace: boolean;
    };
    /** EventAnalysisResult */
    EventAnalysisResult: {
      /**
       * Analysis Run Id
       * Format: uuid
       */
      analysis_run_id: string;
      /** Configuration Hash */
      configuration_hash: string;
      /** Event Count */
      event_count: number;
      /** Profile */
      profile: string;
      /** Reused */
      reused: boolean;
      /**
       * Session Id
       * Format: uuid
       */
      session_id: string;
    };
    /** EventSummary */
    EventSummary: {
      /** By Category */
      by_category: {
        [key: string]: number;
      };
      /** Event Count */
      event_count: number;
      /** Highest Severity */
      highest_severity: ("info" | "low" | "moderate" | "high") | null;
    };
    /** Evidence */
    Evidence: {
      /** Analysis Run Id */
      analysis_run_id?: string | null;
      /** Configuration Id */
      configuration_id?: string | null;
      /** Entity Id */
      entity_id?: string | null;
      /** Event Id */
      event_id?: string | null;
      /** Evidence Type */
      evidence_type: string;
      /** Facts */
      facts?: components["schemas"]["Fact"][];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Provenance */
      provenance?: {
        [key: string]: unknown;
      };
      /** Pull Id */
      pull_id?: string | null;
      /**
       * Run Id
       * Format: uuid
       */
      run_id: string;
      /** Session Id */
      session_id?: string | null;
      /** Source Fingerprint */
      source_fingerprint: string;
      /** Source Tool */
      source_tool: string;
      /** Summary */
      summary: string;
      /**
       * Tool Call Id
       * Format: uuid
       */
      tool_call_id: string;
      /**
       * Truncated
       * @default false
       */
      truncated: boolean;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /** Warnings */
      warnings?: string[];
    };
    /**
     * EvidenceCompleteness
     * @enum {string}
     */
    EvidenceCompleteness: "COMPLETE" | "PARTIAL" | "ABSTAINED";
    /**
     * EvidenceGapCode
     * @enum {string}
     */
    EvidenceGapCode:
      | "NO_FEATURE_SET"
      | "INPUT_ABSTAINED"
      | "SIGNAL_UNAVAILABLE"
      | "FEATURE_NOT_YET_OBSERVED"
      | "LOW_QUALITY"
      | "REFERENCE_INSUFFICIENT"
      | "CONTEXT_INCOMPATIBLE"
      | "UNKNOWN_CONFIG"
      | "MODEL_ARTIFACT_UNAVAILABLE"
      | "PROVENANCE_MISMATCH"
      | "EVIDENCE_SOURCE_MISSING"
      | "SOURCE_SCHEMA_MISMATCH"
      | "CUTOFF_MISMATCH"
      | "UNSUPPORTED_SOURCE"
      | "AMBIGUOUS_ASSOCIATION"
      | "INCOMPLETE_PROJECTION"
      | "UNVERIFIED_SOURCE";
    /**
     * EvidenceHorizon
     * @enum {string}
     */
    EvidenceHorizon: "NEXT_PULL" | "AFTER_PULL_OFFLINE";
    /**
     * EvidenceIntegrity
     * @enum {string}
     */
    EvidenceIntegrity:
      | "VERIFIED"
      | "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE"
      | "FAILED_SOURCE_MISMATCH"
      | "NOT_VERIFIABLE"
      | "UNSUPPORTED_SCHEMA";
    /**
     * EvidenceResultKind
     * @enum {string}
     */
    EvidenceResultKind: "next_pull" | "anomaly";
    /** Fact */
    Fact: {
      /** Path */
      path: string;
      /** Unit */
      unit?: string | null;
      /** Value */
      value: string | number | boolean | null;
    };
    /**
     * Feasibility
     * @enum {string}
     */
    Feasibility:
      | "FEASIBLE"
      | "FEASIBLE_WITH_DEGRADATION"
      | "PARTIALLY_FEASIBLE"
      | "NOT_FEASIBLE";
    /** Finding */
    Finding: {
      /** Bindings */
      bindings: components["schemas"]["Binding"][];
      classification: components["schemas"]["Classification"];
      /** Evidence Ids */
      evidence_ids: string[];
      /** Statement */
      statement: string;
      /**
       * Template
       * @enum {string}
       */
      template:
        | "recorded_fact"
        | "temporal_association"
        | "insufficient_evidence"
        | "thermal_hypothesis"
        | "unsafe_operation_refused"
        | "prediction_result"
        | "anomaly_result"
        | "prediction_insufficient"
        | "statistical_association";
    };
    /**
     * GapStatus
     * @enum {string}
     */
    GapStatus:
      | "OPEN"
      | "AVAILABLE_IN_EXISTING_DATA"
      | "NEEDS_NEW_CAPTURE"
      | "UNAVAILABLE_WITH_CURRENT_SOURCE"
      | "RESOLVED"
      | "WAIVED";
    /**
     * GapType
     * @enum {string}
     */
    GapType:
      | "signal_or_measurement"
      | "comparable_history"
      | "technical_documentation"
      | "data_quality"
      | "configuration_context"
      | "mechanical_cause";
    /** Health */
    Health: {
      /**
       * Status
       * @default ok
       * @constant
       */
      status: "ok";
    };
    /** Hypothesis */
    Hypothesis: {
      category: components["schemas"]["HypothesisCategory"];
      /**
       * Created By
       * @default agent
       */
      created_by: string;
      /** Discriminating Goal */
      discriminating_goal: string;
      /** Evidence Against */
      evidence_against?: string[];
      /** Evidence For */
      evidence_for?: string[];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Limitations */
      limitations?: string[];
      /** Missing Gap Ids */
      missing_gap_ids?: string[];
      /** Statement */
      statement: string;
      /** @default CANDIDATE */
      status: components["schemas"]["HypothesisStatus"];
      /**
       * Support Level
       * @default unknown
       */
      support_level: string;
      /**
       * Updated At
       * Format: date-time
       */
      updated_at?: string;
    };
    /**
     * HypothesisCategory
     * @enum {string}
     */
    HypothesisCategory:
      | "THERMAL"
      | "AIRFLOW_BOOST"
      | "FUELING"
      | "THROTTLE_TORQUE_INTERVENTION"
      | "DATA_QUALITY"
      | "CONFIGURATION_ASSOCIATION"
      | "PERFORMANCE_VARIATION"
      | "UNKNOWN_OTHER";
    /**
     * HypothesisStatus
     * @enum {string}
     */
    HypothesisStatus:
      | "CANDIDATE"
      | "SUPPORTED"
      | "WEAKENED"
      | "NOT_SUPPORTED"
      | "UNRESOLVED"
      | "NOT_TESTABLE_WITH_CURRENT_CAPABILITIES";
    /** ImportResult */
    ImportResult: {
      /** Accepted */
      accepted: number;
      /** Conflicts */
      conflicts: number;
      /** Duplicates */
      duplicates: number;
      /** End Observed At */
      end_observed_at: string | null;
      /** Invalid Timestamps */
      invalid_timestamps: number;
      /** Invalid Units */
      invalid_units: number;
      /** Rejected */
      rejected: number;
      /** Rows Read */
      rows_read: number;
      /**
       * Session Id
       * Format: uuid
       */
      session_id: string;
      /** Start Observed At */
      start_observed_at: string | null;
      /** Unknown Signals */
      unknown_signals: number;
    };
    /** IndexStatus */
    IndexStatus: {
      /** Active */
      active: boolean;
      snapshot: components["schemas"]["KnowledgeIndexVersion"];
    };
    /**
     * Intent
     * @enum {string}
     */
    Intent:
      | "factual"
      | "prediction"
      | "anomaly"
      | "performance"
      | "thermal"
      | "fuel_air_boost"
      | "repeated_degradation"
      | "multi_mechanism"
      | "configuration_comparison"
      | "data_quality"
      | "technical_documentation"
      | "unsafe";
    /** InvestigationEvent */
    InvestigationEvent: {
      /**
       * At
       * Format: date-time
       */
      at?: string;
      /** Detail */
      detail?: string | null;
      /**
       * Investigation Id
       * Format: uuid
       */
      investigation_id: string;
      /**
       * Schema Version
       * @default 1.0
       */
      schema_version: string;
      /** Sequence */
      sequence: number;
      status: components["schemas"]["InvestigationStatus"];
      /** Type */
      type: string;
    };
    /** InvestigationOutcome */
    InvestigationOutcome: {
      /** Classification */
      classification: string;
      /** Conclusion */
      conclusion: string;
      /** Confidence */
      confidence: string;
      /** Evidence Summary */
      evidence_summary?: string[];
      /** Follow Up */
      follow_up?: string | null;
      /** Limitations */
      limitations?: string[];
      /** Resolved Gap Ids */
      resolved_gap_ids?: string[];
      /** Supported Hypothesis Ids */
      supported_hypothesis_ids?: string[];
      /** Unresolved Gap Ids */
      unresolved_gap_ids?: string[];
      /** Weakened Hypothesis Ids */
      weakened_hypothesis_ids?: string[];
    };
    /** InvestigationPlan */
    InvestigationPlan: {
      /**
       * Agent Run Id
       * Format: uuid
       */
      agent_run_id: string;
      approval?: components["schemas"]["Approval"];
      capability_snapshot?: components["schemas"]["CapabilitySnapshot"] | null;
      /** Configuration Id */
      configuration_id?: string | null;
      /**
       * Created At
       * Format: date-time
       */
      created_at?: string;
      /**
       * Cycle Count
       * @default 0
       */
      cycle_count: number;
      /**
       * Findings Summary
       * @default
       */
      findings_summary: string;
      /** Gaps */
      gaps?: components["schemas"]["vehicle_platform__agents__investigation__domain__EvidenceGap"][];
      /** Goal */
      goal: string;
      /** Hypotheses */
      hypotheses?: components["schemas"]["Hypothesis"][];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Linked Session Ids */
      linked_session_ids?: string[];
      outcome?: components["schemas"]["InvestigationOutcome"] | null;
      /**
       * Prompt Version
       * @default investigation-v1
       */
      prompt_version: string;
      /** Question */
      question: string;
      /** Reanalysis Run Id */
      reanalysis_run_id?: string | null;
      recipe?: components["schemas"]["RecipeReference"] | null;
      /**
       * Schema Version
       * @default 1.0
       */
      schema_version: string;
      /** Signal Needs */
      signal_needs?: components["schemas"]["SignalNeed"][];
      /** Source Adapter */
      source_adapter?: ("synthetic" | "replay" | "obd") | null;
      /**
       * Source Id
       * @default
       */
      source_id: string;
      /** Source Session Id */
      source_session_id?: string | null;
      /** @default DRAFT */
      status: components["schemas"]["InvestigationStatus"];
      /** Trace Id */
      trace_id?: string | null;
      /** Transitions */
      transitions?: components["schemas"]["Transition"][];
      /**
       * Updated At
       * Format: date-time
       */
      updated_at?: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /**
       * Version
       * @default 1
       */
      version: number;
    };
    /**
     * InvestigationStatus
     * @enum {string}
     */
    InvestigationStatus:
      | "DRAFT"
      | "EVIDENCE_GAPS_IDENTIFIED"
      | "CAPABILITIES_RESOLVED"
      | "RECIPE_PROPOSED"
      | "AWAITING_APPROVAL"
      | "APPROVED"
      | "ACQUISITION_READY"
      | "AWAITING_DATA"
      | "DATA_RECEIVED"
      | "REANALYZING"
      | "COMPLETED"
      | "INCONCLUSIVE"
      | "REJECTED"
      | "CANCELLED"
      | "FAILED";
    /** KnowledgeCatalog */
    KnowledgeCatalog: {
      /** Chunks */
      chunks: number;
      /** Documents */
      documents: components["schemas"]["DocumentVersion"][];
      /** Embeddings */
      embeddings: number;
      /** Indexes */
      indexes: components["schemas"]["IndexStatus"][];
      /** Sources */
      sources: components["schemas"]["KnowledgeSource"][];
    };
    /** KnowledgeClaim */
    KnowledgeClaim: {
      /**
       * Classification
       * @default DOCUMENTARY_REFERENCE
       * @constant
       */
      classification: "DOCUMENTARY_REFERENCE";
      /**
       * Evidence Id
       * Format: uuid
       */
      evidence_id: string;
      /** Excerpt */
      excerpt: string;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /**
       * Normative
       * @default false
       */
      normative: boolean;
      numeric_fact?: components["schemas"]["NumericFact"] | null;
    };
    /** KnowledgeEvidence */
    KnowledgeEvidence: {
      applicability: components["schemas"]["Match"];
      /** Chunk Checksum */
      chunk_checksum: string;
      /**
       * Chunk Id
       * Format: uuid
       */
      chunk_id: string;
      /** Conflict Ids */
      conflict_ids?: string[];
      document: components["schemas"]["DocumentVersion"];
      /** Fused Score */
      fused_score: number;
      /** Heading Path */
      heading_path: string[];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Index Id */
      index_id: string;
      /** Lexical Score */
      lexical_score: number;
      /** Numeric Facts */
      numeric_facts?: components["schemas"]["NumericFact"][];
      /** Page */
      page: number | null;
      /**
       * Quality
       * @enum {string}
       */
      quality: "reviewed" | "extracted" | "ambiguous";
      /**
       * Retrieval Run Id
       * Format: uuid
       */
      retrieval_run_id: string;
      /** Scope Hash */
      scope_hash: string;
      /** Section */
      section: string;
      /** Snippet */
      snippet: string;
      source: components["schemas"]["KnowledgeSource"];
      /** Vector Score */
      vector_score: number | null;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** KnowledgeIndexVersion */
    KnowledgeIndexVersion: {
      /**
       * Chunker
       * @default heading-table-v1
       */
      chunker: string;
      /** Corpus Checksum */
      corpus_checksum: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /**
       * Dimensions
       * @default 1536
       * @constant
       */
      dimensions: 1536;
      /**
       * Embedding Version
       * @default embedding-cache-v1
       */
      embedding_version: string;
      /** Id */
      id: string;
      /**
       * Lexical
       * @default postgres-simple-or-v2
       */
      lexical: string;
      /**
       * Model
       * @default text-embedding-3-small
       * @constant
       */
      model: "text-embedding-3-small";
      /**
       * Normalization
       * @default utf8-whitespace-v1
       */
      normalization: string;
      /**
       * Ranking
       * @default rrf-trust-applicability-identifiers-v3
       */
      ranking: string;
    };
    /** KnowledgeQuery */
    KnowledgeQuery: {
      intent: components["schemas"]["RetrievalIntent"];
      /** Session Id */
      session_id?: string | null;
    };
    /** KnowledgeReport */
    KnowledgeReport: {
      /** Claims */
      claims?: components["schemas"]["KnowledgeClaim"][];
      /**
       * Request Type
       * @enum {string}
       */
      request_type:
        | "KNOWLEDGE_FACT"
        | "HYBRID_COMPARISON"
        | "TECHNICAL_KNOWLEDGE_INSUFFICIENT"
        | "VEHICLE_EVIDENCE_INSUFFICIENT";
      retrieval: components["schemas"]["RetrievalResult"];
      /**
       * Schema Version
       * @default 1.0
       * @constant
       */
      schema_version: "1.0";
    };
    /** KnowledgeSource */
    KnowledgeSource: {
      /** Canonical Url */
      canonical_url: string;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Publisher */
      publisher: string;
      /**
       * Source Type
       * @enum {string}
       */
      source_type:
        | "oem_training"
        | "oem_service"
        | "oem_press"
        | "supplier"
        | "tuner"
        | "internal"
        | "community";
      /** @default UNVERIFIED */
      status: components["schemas"]["SourceStatus"];
      trust: components["schemas"]["Trust"];
      /** Verified At */
      verified_at?: string | null;
      /**
       * Version
       * @default 1
       */
      version: number;
    };
    /** LinkSessionRequest */
    LinkSessionRequest: {
      /**
       * Session Id
       * Format: uuid
       */
      session_id: string;
      /** Version */
      version: number;
    };
    /** LiveSignalQuality */
    LiveSignalQuality: {
      /** Actual Hz */
      actual_hz: number;
      /** Jitter Ms */
      jitter_ms?: number | null;
      /** Missing Ratio */
      missing_ratio: number;
      /** Signal */
      signal: string;
      /** Stale Ratio */
      stale_ratio: number;
      /** Target Hz */
      target_hz: number;
    };
    /** LiveTelemetryPoint */
    LiveTelemetryPoint: {
      /**
       * Observed At
       * Format: date-time
       */
      observed_at: string;
      /** Signal */
      signal: string;
      /** Unit */
      unit: string;
      /** Value */
      value: number;
    };
    /** LoggingRecipeResponse */
    LoggingRecipeResponse: {
      /** Configuration Hash */
      configuration_hash: string;
      /** Description */
      description: string;
      /** Key */
      key: string;
      /** Minimum Duration Seconds */
      minimum_duration_seconds: number;
      /** Name */
      name: string;
      /** Notes */
      notes: string[];
      /** Objective */
      objective: string;
      /** Requirements */
      requirements: components["schemas"]["RecipeSignal"][];
      /** Supported Modes */
      supported_modes: string[];
      /** Vehicle Scope */
      vehicle_scope: string;
      /** Version */
      version: number;
    };
    /**
     * MLTask
     * @enum {string}
     */
    MLTask:
      | "NEXT_PULL_THERMAL_DEGRADATION"
      | "NEXT_PULL_PERFORMANCE_DEGRADATION"
      | "NEXT_PULL_FUEL_DEVIATION";
    /** Match */
    Match: {
      /**
       * Normative
       * @default false
       */
      normative: boolean;
      /** Reasons */
      reasons: string[];
      /** Score */
      score: number;
      /**
       * Status
       * @enum {string}
       */
      status: "APPLICABLE" | "PARTIAL" | "UNKNOWN" | "INCOMPATIBLE";
    };
    /** Modification */
    Modification: {
      /** Category */
      category: string;
      /** Configuration Id */
      configuration_id?: string | null;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /**
       * Installed At
       * Format: date-time
       */
      installed_at: string;
      /** Manufacturer */
      manufacturer?: string | null;
      /** Notes */
      notes?: string | null;
      /** Product */
      product?: string | null;
      /** Removed At */
      removed_at?: string | null;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** ModificationCreate */
    ModificationCreate: {
      /** Category */
      category: string;
      /** Configuration Id */
      configuration_id?: string | null;
      /**
       * Installed At
       * Format: date-time
       */
      installed_at: string;
      /** Manufacturer */
      manufacturer?: string | null;
      /** Notes */
      notes?: string | null;
      /** Product */
      product?: string | null;
      /** Removed At */
      removed_at?: string | null;
    };
    /** NextPullRequest */
    NextPullRequest: {
      /** Model Version Id */
      model_version_id?: string | null;
      /**
       * Observation Cutoff
       * Format: date-time
       */
      observation_cutoff: string;
      /**
       * Pull Id
       * Format: uuid
       */
      pull_id: string;
      source_role: components["schemas"]["SourceRole"];
      task: components["schemas"]["MLTask"];
      /** Vehicle Id */
      vehicle_id?: string | null;
    };
    /** NumericFact */
    NumericFact: {
      /** Conditions */
      conditions: string;
      /**
       * Kind
       * @default descriptive
       * @enum {string}
       */
      kind: "descriptive" | "stock_target" | "tune_target" | "service_limit";
      /** Original */
      original: string;
      /** Topic */
      topic?:
        | (
            | "architecture"
            | "fuel"
            | "boost"
            | "thermal"
            | "calibration"
            | "diagnostics"
          )
        | null;
      /** Unit */
      unit: string;
      /** Value */
      value: number;
    };
    /** ObjectiveResponse */
    ObjectiveResponse: {
      /** Key */
      key: string;
      /** Recipe Key */
      recipe_key: string;
    };
    /** PredictionBindingResponse */
    PredictionBindingResponse: {
      /**
       * Activation Event Id
       * Format: uuid
       */
      activation_event_id: string;
      /** Artifact Checksum */
      artifact_checksum: string;
      /**
       * Binding Id
       * Format: uuid
       */
      binding_id: string;
      /** Detector Version Id */
      detector_version_id: string | null;
      /** Environment */
      environment: string;
      /** Feature Set Checksum */
      feature_set_checksum: string;
      /** Feature Set Version */
      feature_set_version: string;
      /** Model Version Id */
      model_version_id: string | null;
      /** Result Kind */
      result_kind: string;
      /** Schema Checksum */
      schema_checksum: string;
      /** Scope */
      scope: string;
      /** Source Role */
      source_role: string;
      /** Subject Key */
      subject_key: string;
    };
    /** PredictionEvidenceMaterializeRequest */
    PredictionEvidenceMaterializeRequest: {
      /**
       * Schema Version
       * @default phase9e-prediction-evidence-v1
       * @constant
       */
      schema_version: "phase9e-prediction-evidence-v1";
    };
    /** PredictionEvidenceMaterializeResponse */
    PredictionEvidenceMaterializeResponse: {
      evidence: components["schemas"]["PredictionEvidenceProjection"];
      /** Materialized */
      materialized: boolean;
    };
    /** PredictionEvidenceProjection */
    PredictionEvidenceProjection: {
      artifact_availability: components["schemas"]["ArtifactAvailability"];
      /** Available Signals */
      available_signals?: string[];
      /** Claims */
      claims: {
        [key: string]: unknown;
      }[];
      completeness: components["schemas"]["EvidenceCompleteness"];
      /** Coverage */
      coverage: number;
      /**
       * Cutoff
       * Format: date-time
       */
      cutoff: string;
      /** Decision */
      decision: boolean | ("ANOMALOUS" | "INLIER") | null;
      /** Duplicate Timestamp Count */
      duplicate_timestamp_count?: number | null;
      /** Edge Count */
      edge_count: number;
      /**
       * Evidence Id
       * Format: uuid
       */
      evidence_id: string;
      /** Expected Feature Count */
      expected_feature_count: number;
      /** Fact Count */
      fact_count: number;
      /** Facts */
      facts: {
        [key: string]: unknown;
      }[];
      /** Family */
      family: string | null;
      /** Fingerprint */
      fingerprint: string;
      /** Gaps */
      gaps: components["schemas"]["vehicle_platform__prediction_evidence__domain__EvidenceGap"][];
      horizon: components["schemas"]["EvidenceHorizon"];
      integrity: components["schemas"]["EvidenceIntegrity"];
      /** Interpretation */
      interpretation: string;
      /** Invalid Observation Count */
      invalid_observation_count?: number | null;
      /** Limitations */
      limitations: string[];
      /** Missing Reason Counts */
      missing_reason_counts?: {
        [key: string]: number;
      };
      /** Node Count */
      node_count: number;
      /** Observed Feature Count */
      observed_feature_count: number;
      /** Omitted Count */
      omitted_count: number;
      /** Pull Completeness */
      pull_completeness?: number | null;
      /** Reason Code */
      reason_code: string | null;
      /**
       * Receipt Id
       * Format: uuid
       */
      receipt_id: string;
      result_type: components["schemas"]["EvidenceResultKind"];
      /**
       * Schema Version
       * @constant
       */
      schema_version: "phase9e-safe-projection-v1";
      /** Score */
      score: number | null;
      /**
       * Score Is Probability
       * @default false
       * @constant
       */
      score_is_probability: false;
      source_role: components["schemas"]["SourceRole"];
      /** Source Type */
      source_type?: string | null;
      /** Status */
      status: string;
      /** Task */
      task: string | null;
      /** Threshold */
      threshold: number | null;
    };
    /** PredictionLineage */
    PredictionLineage: {
      /** Anomaly Finding Id */
      anomaly_finding_id?: string | null;
      /** Anomaly Run Id */
      anomaly_run_id?: string | null;
      /** Feature Set Id */
      feature_set_id?: string | null;
    };
    /** PredictionQuality */
    PredictionQuality: {
      /** Coverage */
      coverage: number;
      /** Expected Feature Count */
      expected_feature_count: number;
      /** Missing Reason Counts */
      missing_reason_counts?: {
        [key: string]: number;
      };
      /** Observed Feature Count */
      observed_feature_count: number;
      /**
       * Quality Class
       * @enum {string}
       */
      quality_class: "high" | "degraded" | "insufficient" | "unavailable";
    };
    /** PredictionResponse */
    PredictionResponse: {
      /** Anomaly Score */
      anomaly_score?: number | null;
      /** Decision */
      decision?: boolean | ("ANOMALOUS" | "INLIER") | null;
      /** Detector Version Id */
      detector_version_id?: string | null;
      /** Effective Cutoff */
      effective_cutoff?: string | null;
      /** Engineering Validation Score */
      engineering_validation_score?: number | null;
      /** Family */
      family?: ("thermal" | "boost_air" | "performance" | "fuel") | null;
      /** Feature Set Version */
      feature_set_version?: string | null;
      /**
       * Horizon
       * @enum {string}
       */
      horizon: "NEXT_PULL" | "AFTER_PULL_OFFLINE";
      /** Interpretation */
      interpretation: string;
      /** Limitation */
      limitation: string;
      lineage: components["schemas"]["PredictionLineage"];
      /** Model Version Id */
      model_version_id?: string | null;
      quality: components["schemas"]["PredictionQuality"];
      /** Reason Code */
      reason_code?: string | null;
      /**
       * Receipt Id
       * Format: uuid
       */
      receipt_id: string;
      /**
       * Requested Cutoff
       * Format: date-time
       */
      requested_cutoff: string;
      /**
       * Result Type
       * @enum {string}
       */
      result_type: "next_pull" | "anomaly";
      /**
       * Schema Version
       * @default phase9d-prediction-response-v1
       * @constant
       */
      schema_version: "phase9d-prediction-response-v1";
      /**
       * Score Is Probability
       * @default false
       * @constant
       */
      score_is_probability: false;
      source_role: components["schemas"]["SourceRole"];
      status: components["schemas"]["PredictionStatus"];
      task?: components["schemas"]["MLTask"] | null;
      /** Threshold */
      threshold?: number | null;
    };
    /**
     * PredictionStatus
     * @enum {string}
     */
    PredictionStatus:
      | "READY_SCORE"
      | "ABSTAINED_INSUFFICIENT_SIGNAL"
      | "ABSTAINED_LOW_QUALITY"
      | "ABSTAINED_INSUFFICIENT_REFERENCE"
      | "ABSTAINED_INCOMPATIBLE_CONTEXT"
      | "ABSTAINED_UNSUPPORTED_SOURCE"
      | "ABSTAINED_CUTOFF";
    /** PredictionVersionsResponse */
    PredictionVersionsResponse: {
      /** Items */
      items: components["schemas"]["PredictionBindingResponse"][];
      /** Limit */
      limit: number;
      /** Offset */
      offset: number;
      /**
       * Schema Version
       * @default phase9d-serving-versions-v1
       */
      schema_version: string;
    };
    /** PreflightRequest */
    PreflightRequest: {
      /** Adapter */
      adapter: string;
      /**
       * Discovery Supported
       * @default true
       */
      discovery_supported: boolean;
      /** Maximum Requests Per Second */
      maximum_requests_per_second: number;
      /** Signals */
      signals: {
        [key: string]:
          | "supported"
          | "unsupported"
          | "unavailable"
          | "unknown"
          | "adapter_does_not_support_discovery";
      };
    };
    /** PreflightResponse */
    PreflightResponse: {
      /** Expected Capabilities */
      expected_capabilities: string[];
      /** Optional Available */
      optional_available: string[];
      /**
       * Readiness
       * @enum {string}
       */
      readiness: "ready" | "degraded" | "blocked";
      /** Recommended Available */
      recommended_available: string[];
      /** Required Available */
      required_available: string[];
      /** Required Missing */
      required_missing: string[];
      /**
       * Sampling Algorithm Version
       * @default 1.1
       * @constant
       */
      sampling_algorithm_version: "1.1";
      /** Sampling Plan */
      sampling_plan: components["schemas"]["SamplingPlanResponse"][];
      /** Unavailable Capabilities */
      unavailable_capabilities: string[];
      /** Warnings */
      warnings: string[];
    };
    /** ProvisionalFindingResponse */
    ProvisionalFindingResponse: {
      /** Canonical Reference */
      canonical_reference?: string | null;
      /** Category */
      category: string;
      /** Ended At */
      ended_at: string | null;
      /** Evidence */
      evidence: {
        [key: string]: unknown;
      };
      /** Finding Type */
      finding_type: string;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Reconciliation Status */
      reconciliation_status: string;
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
    };
    /** Pull */
    Pull: {
      /** Algorithm Version */
      algorithm_version: string;
      /** Average Boost */
      average_boost: number | null;
      /** Average Throttle */
      average_throttle: number | null;
      /** Confidence */
      confidence: number;
      /** Configuration Hash */
      configuration_hash: string;
      /** Configuration Id */
      configuration_id: string | null;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Data Completeness */
      data_completeness: number;
      /** Detector Name */
      detector_name: string;
      /** Duration Ms */
      duration_ms: number;
      /** End Iat */
      end_iat: number | null;
      /** End Rpm */
      end_rpm: number | null;
      /** End Speed */
      end_speed: number | null;
      /**
       * Ended At
       * Format: date-time
       */
      ended_at: string;
      /** Iat Delta */
      iat_delta: number | null;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Max Boost */
      max_boost: number | null;
      /** Max Coolant Temperature */
      max_coolant_temperature: number | null;
      /** Max Oil Temperature */
      max_oil_temperature: number | null;
      /** Max Rpm */
      max_rpm: number | null;
      /** Max Speed */
      max_speed: number | null;
      /** Max Throttle */
      max_throttle: number | null;
      /** Metadata */
      metadata: {
        [key: string]: unknown;
      };
      /** Min Rpm */
      min_rpm: number | null;
      /** Quality Flags */
      quality_flags: string[];
      /** Sample Count */
      sample_count: number;
      /** Segment Id */
      segment_id: string | null;
      /**
       * Session Id
       * Format: uuid
       */
      session_id: string;
      /** Start Iat */
      start_iat: number | null;
      /** Start Rpm */
      start_rpm: number | null;
      /** Start Speed */
      start_speed: number | null;
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** Ready */
    Ready: {
      /**
       * Database
       * @default ready
       * @constant
       */
      database: "ready";
      /**
       * Status
       * @default ready
       * @constant
       */
      status: "ready";
    };
    /** RecipeReference */
    RecipeReference: {
      /** Configuration Hash */
      configuration_hash: string;
      /** Dropped Signals */
      dropped_signals?: string[];
      feasibility: components["schemas"]["Feasibility"];
      /** Key */
      key: string;
      /** Minimum Duration Seconds */
      minimum_duration_seconds: number;
      /** Rate Compromises */
      rate_compromises?: string[];
      /** Rationale */
      rationale?: string[];
      /** Required Missing */
      required_missing?: string[];
      /** Sampling Algorithm Version */
      sampling_algorithm_version: string;
      /** Source */
      source: string;
      /** Supported Modes */
      supported_modes: string[];
      /** Vehicle Scope */
      vehicle_scope: string;
      /** Version */
      version: number;
    };
    /** RecipeSignal */
    RecipeSignal: {
      /**
       * Importance
       * @enum {string}
       */
      importance: "required" | "recommended" | "optional";
      /** Minimum Hz */
      minimum_hz: number;
      /** Missing Effect */
      missing_effect: string[];
      /** Preferred Hz */
      preferred_hz: number;
      /**
       * Priority
       * @enum {string}
       */
      priority: "critical_for_recipe" | "high" | "normal" | "low";
      /** Reason */
      reason: string;
      /** Signal */
      signal: string;
    };
    /** RegisterSourcePreflight */
    RegisterSourcePreflight: {
      /**
       * Adapter
       * @enum {string}
       */
      adapter: "obd" | "replay";
      capability_snapshot: components["schemas"]["PreflightRequest"];
      /**
       * Configuration Id
       * Format: uuid
       */
      configuration_id: string;
      /** Source Id */
      source_id: string;
    };
    /**
     * Resolution
     * @enum {string}
     */
    Resolution: "HIGH" | "MEDIUM" | "LOW" | "EVENT_CONTEXT";
    /** RetrievalIntent */
    RetrievalIntent: {
      /**
       * Need
       * @default principle
       * @enum {string}
       */
      need: "principle" | "normative_target";
      /** Query */
      query: string;
      /** Source Tuner */
      source_tuner?: string | null;
      /**
       * Top K
       * @default 5
       */
      top_k: number;
      /**
       * Topic
       * @enum {string}
       */
      topic:
        | "architecture"
        | "fuel"
        | "boost"
        | "thermal"
        | "calibration"
        | "diagnostics";
    };
    /** RetrievalResult */
    RetrievalResult: {
      /** Candidate Count */
      candidate_count: number;
      /** Evidence */
      evidence?: components["schemas"]["KnowledgeEvidence"][];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Index Id */
      index_id: string;
      intent: components["schemas"]["RetrievalIntent"];
      /** Knowledge Gaps */
      knowledge_gaps?: string[];
      /** Latency Seconds */
      latency_seconds: number;
      scope: components["schemas"]["VehicleScope"];
      /** Source Conflicts */
      source_conflicts?: components["schemas"]["SourceConflict"][];
      /** Timings */
      timings?: {
        [key: string]: number;
      };
      /**
       * Vector Available
       * @default false
       */
      vector_available: boolean;
      /**
       * Wrong Platform Rejections
       * @default 0
       */
      wrong_platform_rejections: number;
    };
    /** RoutingDecision */
    RoutingDecision: {
      /** Considered */
      considered: components["schemas"]["Specialist"][];
      /** Data Quality Gate */
      data_quality_gate: boolean;
      /** Hints */
      hints: string[];
      intent: components["schemas"]["Intent"];
      /** Reason */
      reason: string;
      /** Selected */
      selected: components["schemas"]["Specialist"][];
      /** Skipped */
      skipped: components["schemas"]["Specialist"][];
    };
    /** RunAudit */
    RunAudit: {
      /** Evidence */
      evidence: components["schemas"]["Evidence"][];
      /**
       * Run Id
       * Format: uuid
       */
      run_id: string;
      /** Tool Calls */
      tool_calls: components["schemas"]["ToolCall"][];
    };
    /** SamplingPlanResponse */
    SamplingPlanResponse: {
      /** Estimated Hz */
      estimated_hz: number;
      /** Priority */
      priority: string;
      /** Signal */
      signal: string;
      /** Target Hz */
      target_hz: number;
    };
    /** SessionCreate */
    SessionCreate: {
      /** Configuration Id */
      configuration_id?: string | null;
      /** Ended At */
      ended_at?: string | null;
      /** Metadata */
      metadata?: {
        [key: string]: unknown;
      };
      /** Source Reference */
      source_reference?: string | null;
      /** Source Timezone */
      source_timezone?: string | null;
      /**
       * Source Type
       * @enum {string}
       */
      source_type: "csv" | "synthetic" | "obd";
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** SessionSegment */
    SessionSegment: {
      /** Algorithm Version */
      algorithm_version: string;
      /** Confidence */
      confidence: number;
      /** Configuration Hash */
      configuration_hash: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Detector Name */
      detector_name: string;
      /** Duration Ms */
      duration_ms: number;
      /**
       * Ended At
       * Format: date-time
       */
      ended_at: string;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Metadata */
      metadata: {
        [key: string]: unknown;
      };
      /** Quality Flags */
      quality_flags: string[];
      /**
       * Segment Type
       * @enum {string}
       */
      segment_type:
        | "idle"
        | "warm_up"
        | "cruise"
        | "acceleration"
        | "pull"
        | "deceleration"
        | "unknown";
      /**
       * Session Id
       * Format: uuid
       */
      session_id: string;
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
    };
    /** Signal */
    Signal: {
      /** Aliases */
      aliases: string[];
      /** Category */
      category: string;
      /** Key */
      key: string;
      /** Maximum */
      maximum: number;
      /** Minimum */
      minimum: number;
      /** Name */
      name: string;
      /** Unit */
      unit: string;
    };
    /** SignalNeed */
    SignalNeed: {
      /** @default UNKNOWN */
      availability: components["schemas"]["Availability"];
      /** Canonical Signal */
      canonical_signal?: string | null;
      /** Gap Ids */
      gap_ids: string[];
      /** Hypothesis Ids */
      hypothesis_ids?: string[];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /**
       * Provenance
       * @default unresolved
       */
      provenance: string;
      /** Recorded In Session */
      recorded_in_session?: boolean | null;
      /** Required */
      required: boolean;
      resolution: components["schemas"]["Resolution"];
      role: components["schemas"]["SignalRole"];
      /** @default UNKNOWN */
      source_support: components["schemas"]["Availability"];
      /** Unavailable Reason */
      unavailable_reason?: string | null;
    };
    /**
     * SignalRole
     * @enum {string}
     */
    SignalRole:
      | "engine_speed_context"
      | "vehicle_speed_context"
      | "throttle_opening_behavior"
      | "boost_pressure_behavior"
      | "intake_temperature_behavior"
      | "coolant_temperature_context"
      | "oil_temperature_context"
      | "high_fuel_pressure_behavior"
      | "low_fuel_pressure_behavior"
      | "lambda_behavior"
      | "timing_behavior"
      | "timestamp_sequence_quality";
    /** SourceConflict */
    SourceConflict: {
      /** Explanation */
      explanation: string;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /**
       * Left Version Id
       * Format: uuid
       */
      left_version_id: string;
      /**
       * Right Version Id
       * Format: uuid
       */
      right_version_id: string;
      /**
       * Status
       * @default OPEN
       * @enum {string}
       */
      status: "OPEN" | "RESOLVED";
      /**
       * Topic
       * @enum {string}
       */
      topic:
        | "architecture"
        | "fuel"
        | "boost"
        | "thermal"
        | "calibration"
        | "diagnostics";
    };
    /**
     * SourceRole
     * @enum {string}
     */
    SourceRole:
      "synthetic" | "real_vehicle" | "imported" | "imported_fixture" | "mixed";
    /**
     * SourceStatus
     * @enum {string}
     */
    SourceStatus: "VERIFIED" | "UNVERIFIED" | "QUARANTINED" | "REJECTED";
    /**
     * Specialist
     * @enum {string}
     */
    Specialist: "data_quality" | "performance" | "thermal" | "fuel_air_boost";
    /** SpecialistBudget */
    SpecialistBudget: {
      /**
       * Evidence Items
       * @default 32
       */
      evidence_items: number;
      /**
       * Mcp Calls
       * @default 6
       */
      mcp_calls: number;
      /**
       * Model Turns
       * @default 4
       */
      model_turns: number;
      /**
       * Result Bytes
       * @default 16384
       */
      result_bytes: number;
      /**
       * Telemetry Windows
       * @default 0
       */
      telemetry_windows: number;
      /**
       * Timeout Seconds
       * @default 25
       */
      timeout_seconds: number;
    };
    /** SpecialistFinding */
    SpecialistFinding: {
      /** Bindings */
      bindings: components["schemas"]["Binding"][];
      classification: components["schemas"]["Classification"];
      /** Configuration Ids */
      configuration_ids?: string[];
      /** Evidence Ids */
      evidence_ids: string[];
      /**
       * Finding Id
       * Format: uuid
       */
      finding_id: string;
      /** Limitations */
      limitations?: string[];
      /** Session Ids */
      session_ids?: string[];
      specialist: components["schemas"]["Specialist"];
      /** Statement */
      statement: string;
      /**
       * Strength
       * @enum {string}
       */
      strength: "low" | "moderate" | "high";
      /**
       * Template
       * @enum {string}
       */
      template:
        | "recorded_fact"
        | "temporal_association"
        | "insufficient_evidence"
        | "thermal_hypothesis"
        | "unsafe_operation_refused"
        | "prediction_result"
        | "anomaly_result"
        | "prediction_insufficient"
        | "statistical_association";
    };
    /** SpecialistResult */
    SpecialistResult: {
      /**
       * Blocks Interpretation
       * @default false
       */
      blocks_interpretation: boolean;
      budget?: components["schemas"]["SpecialistBudget"] | null;
      /**
       * Cache Hits
       * @default 0
       */
      cache_hits: number;
      /**
       * Confidence
       * @default low
       * @enum {string}
       */
      confidence: "low" | "moderate" | "high";
      /** Data Quality Warnings */
      data_quality_warnings?: string[];
      /**
       * Duration Seconds
       * @default 0
       */
      duration_seconds: number;
      /** Error Category */
      error_category?: string | null;
      /** Evidence Gaps */
      evidence_gaps?: (
        | "mechanical_cause"
        | "signal_or_measurement"
        | "comparable_history"
        | "technical_documentation"
        | "data_quality"
        | "configuration_context"
      )[];
      /** Evidence Ids */
      evidence_ids?: string[];
      /** Findings */
      findings?: components["schemas"]["SpecialistFinding"][];
      /**
       * Model Turn Count
       * @default 0
       */
      model_turn_count: number;
      /** Prompt Version */
      prompt_version: string;
      /**
       * Schema Version
       * @default 1.0
       * @constant
       */
      schema_version: "1.0";
      specialist: components["schemas"]["Specialist"];
      /**
       * Status
       * @enum {string}
       */
      status: "completed" | "failed" | "timed_out" | "cancelled" | "skipped";
      /**
       * Supervisor Run Id
       * Format: uuid
       */
      supervisor_run_id: string;
      /**
       * Telemetry Call Count
       * @default 0
       */
      telemetry_call_count: number;
      /**
       * Tool Call Count
       * @default 0
       */
      tool_call_count: number;
      /** Trace Id */
      trace_id?: string | null;
      usage?: components["schemas"]["Usage"];
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** StreamEvent */
    StreamEvent: {
      /** Data */
      data?: {
        [key: string]: unknown;
      };
      /**
       * Run Id
       * Format: uuid
       */
      run_id: string;
      /**
       * Schema Version
       * @default 1.0
       * @enum {string}
       */
      schema_version: "1.0" | "1.1";
      /** Sequence */
      sequence: number;
      /**
       * Type
       * @enum {string}
       */
      type:
        | "run_started"
        | "context_resolved"
        | "tool_started"
        | "tool_completed"
        | "evidence_added"
        | "answer_chunk"
        | "run_completed"
        | "run_failed"
        | "run_cancelled"
        | "supervisor_started"
        | "routing_completed"
        | "specialist_started"
        | "specialist_tool_started"
        | "specialist_tool_completed"
        | "specialist_completed"
        | "specialist_failed"
        | "conflict_detected"
        | "sufficiency_evaluated"
        | "investigation_proposed"
        | "synthesis_started";
    };
    /** StreamObservation */
    StreamObservation: {
      /**
       * Message Id
       * Format: uuid
       */
      message_id: string;
      /**
       * Observed At
       * Format: date-time
       */
      observed_at: string;
      /** Sequence */
      sequence?: number | null;
      /** Signal */
      signal: string;
      /** Source Record Id */
      source_record_id: string;
      /** Unit */
      unit: string;
      /** Value */
      value: number;
    };
    /**
     * Sufficiency
     * @enum {string}
     */
    Sufficiency:
      | "SUFFICIENT"
      | "PARTIALLY_SUFFICIENT"
      | "INSUFFICIENT"
      | "UNRELIABLE_DATA";
    /** SupervisorLimits */
    SupervisorLimits: {
      /** Concurrent Specialists */
      concurrent_specialists: number;
      /** Evidence Items */
      evidence_items: number;
      /** Input Bytes */
      input_bytes: number;
      /** Mcp Calls */
      mcp_calls: number;
      /** Model Turns */
      model_turns: number;
      /**
       * Prediction Evidence Reads
       * @default 0
       */
      prediction_evidence_reads: number;
      /** Retries */
      retries: number;
      /** Specialists */
      specialists: number;
      /** Telemetry Windows */
      telemetry_windows: number;
      /** Timeout Seconds */
      timeout_seconds: number;
      /** Tool Result Bytes */
      tool_result_bytes: number;
    };
    /** SupervisorReport */
    SupervisorReport: {
      /**
       * Cache Hits
       * @default 0
       */
      cache_hits: number;
      /** Configuration Hash */
      configuration_hash?: string | null;
      /** Conflicts */
      conflicts?: components["schemas"]["Conflict"][];
      /** Evidence Consumers */
      evidence_consumers?: {
        [key: string]: components["schemas"]["Specialist"][];
      };
      /** Investigation Id */
      investigation_id?: string | null;
      /**
       * Investigation Recommended
       * @default false
       */
      investigation_recommended: boolean;
      limits?: components["schemas"]["SupervisorLimits"] | null;
      /**
       * Model Turn Count
       * @default 0
       */
      model_turn_count: number;
      /**
       * Prompt Version
       * @default supervisor-v3
       * @enum {string}
       */
      prompt_version:
        "supervisor-v1" | "supervisor-v2" | "supervisor-v3" | "supervisor-v4";
      /**
       * Retry Count
       * @default 0
       */
      retry_count: number;
      routing: components["schemas"]["RoutingDecision"];
      /**
       * Routing Seconds
       * @default 0
       */
      routing_seconds: number;
      routing_usage?: components["schemas"]["Usage"];
      /**
       * Schema Version
       * @default 1.1
       * @enum {string}
       */
      schema_version: "1.0" | "1.1";
      /** Specialists */
      specialists?: components["schemas"]["SpecialistResult"][];
      /** @default INSUFFICIENT */
      sufficiency: components["schemas"]["Sufficiency"];
      synthesis_usage?: components["schemas"]["Usage"];
    };
    /**
     * Support
     * @enum {string}
     */
    Support:
      | "supported"
      | "unsupported"
      | "unavailable"
      | "unknown"
      | "adapter_does_not_support_discovery";
    /** TelemetryPoint */
    TelemetryPoint: {
      /**
       * Observed At
       * Format: date-time
       */
      observed_at: string;
      /** Quality */
      quality: string;
      /** Sample Id */
      sample_id: string;
      /** Sequence */
      sequence: number | null;
      /** Signal */
      signal: string;
      /** Unit */
      unit: string;
      /** Value */
      value: number;
    };
    /** TelemetryWindow */
    TelemetryWindow: {
      /** End */
      end: string | null;
      /** Points */
      points: components["schemas"]["TelemetryPoint"][];
      /** Returned */
      returned: number;
      /**
       * Session Id
       * Format: uuid
       */
      session_id: string;
      /** Start */
      start: string | null;
      /** Truncated */
      truncated: boolean;
    };
    /** ToolCall */
    ToolCall: {
      /** Argument Hash */
      argument_hash: string;
      /** Completed At */
      completed_at?: string | null;
      /** Duration Seconds */
      duration_seconds?: number | null;
      /** Error Category */
      error_category?: string | null;
      /** Evidence Ids */
      evidence_ids?: string[];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Mcp Request Id */
      mcp_request_id?: string | null;
      /**
       * Returned
       * @default 0
       */
      returned: number;
      /**
       * Run Id
       * Format: uuid
       */
      run_id: string;
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      /**
       * Status
       * @default running
       * @enum {string}
       */
      status: "running" | "completed" | "failed";
      /** Tool Name */
      tool_name: string;
      /**
       * Truncated
       * @default false
       */
      truncated: boolean;
    };
    /** Transition */
    Transition: {
      /**
       * At
       * Format: date-time
       */
      at: string;
      status: components["schemas"]["InvestigationStatus"];
    };
    /**
     * Trust
     * @enum {string}
     */
    Trust:
      | "TIER_1_AUTHORITATIVE"
      | "TIER_2_STRONG_TECHNICAL"
      | "TIER_3_CURATED_INTERNAL"
      | "TIER_4_COMMUNITY";
    /** Usage */
    Usage: {
      /** Cached Input Tokens */
      cached_input_tokens?: number | null;
      /** Estimated Cost */
      estimated_cost?: number | null;
      /** Input Tokens */
      input_tokens?: number | null;
      /** Output Tokens */
      output_tokens?: number | null;
      /** Pricing Version */
      pricing_version?: string | null;
      /** Total Tokens */
      total_tokens?: number | null;
    };
    /** Vehicle */
    Vehicle: {
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Engine Code */
      engine_code?: string | null;
      /** Generation */
      generation?: string | null;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Manufacturer */
      manufacturer: string;
      /** Model */
      model: string;
      /** Model Year */
      model_year?: number | null;
      /** Nickname */
      nickname?: string | null;
      /** Transmission */
      transmission?: string | null;
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string;
      /** Vin */
      vin?: string | null;
    };
    /** VehicleConfiguration */
    VehicleConfiguration: {
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Description */
      description: string;
      /**
       * Effective At
       * Format: date-time
       */
      effective_at: string;
      /** Ended At */
      ended_at?: string | null;
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /** Metadata */
      metadata?: {
        [key: string]: unknown;
      };
      /** Provenance */
      provenance: string;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** VehicleContext */
    VehicleContext: {
      /** Active Configuration Id */
      active_configuration_id?: string | null;
      /**
       * As Of
       * Format: date-time
       */
      as_of: string;
      /** Capabilities */
      capabilities?: {
        [key: string]: {
          [key: string]: unknown;
        };
      };
      /** Configurations */
      configurations?: {
        [key: string]: unknown;
      }[];
      /** Modifications */
      modifications?: {
        [key: string]: unknown;
      }[];
      /** Sessions */
      sessions?: {
        [key: string]: unknown;
      }[];
      /** Vehicle */
      vehicle?: {
        [key: string]: unknown;
      };
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
      /** Warnings */
      warnings?: string[];
    };
    /** VehicleCreate */
    VehicleCreate: {
      /** Engine Code */
      engine_code?: string | null;
      /** Generation */
      generation?: string | null;
      /** Manufacturer */
      manufacturer: string;
      /** Model */
      model: string;
      /** Model Year */
      model_year?: number | null;
      /** Nickname */
      nickname?: string | null;
      /** Transmission */
      transmission?: string | null;
      /** Vin */
      vin?: string | null;
    };
    /** VehicleScope */
    VehicleScope: {
      /**
       * As Of
       * Format: date-time
       */
      as_of: string;
      /**
       * Calibration
       * @default unknown
       * @enum {string}
       */
      calibration: "unknown" | "stock" | "tuned";
      /** Configuration Id */
      configuration_id?: string | null;
      /** Engine */
      engine?: string | null;
      /** Engine Variant */
      engine_variant?: string | null;
      /** Fuel */
      fuel?: string | null;
      /** Hardware */
      hardware?: string[];
      /** Make */
      make?: string | null;
      /** Map Version */
      map_version?: string | null;
      /** Model */
      model?: string | null;
      /** Model Year */
      model_year?: number | null;
      /** Part Numbers */
      part_numbers?: string[];
      /** Platform */
      platform?: string | null;
      /** Region */
      region?: string | null;
      /** Session Id */
      session_id?: string | null;
      /** Stage */
      stage?: string | null;
      /**
       * Temporal Valid
       * @default false
       */
      temporal_valid: boolean;
      /** Transmission */
      transmission?: string | null;
      /** Tuner */
      tuner?: string | null;
      /**
       * Vehicle Id
       * Format: uuid
       */
      vehicle_id: string;
    };
    /** VehicleUpdate */
    VehicleUpdate: {
      /** Nickname */
      nickname?: string | null;
      /** Transmission */
      transmission?: string | null;
    };
    /** Version */
    Version: {
      /**
       * Application
       * @default vehicle-intelligence-platform
       */
      application: string;
      /** Build Timestamp */
      build_timestamp: string | null;
      /**
       * Environment
       * @enum {string}
       */
      environment: "development" | "test" | "production";
      /** Git Sha */
      git_sha: string | null;
      /** Version */
      version: string;
    };
    /** VersionRequest */
    VersionRequest: {
      /** Version */
      version: number;
    };
    /** EvidenceGap */
    vehicle_platform__agents__investigation__domain__EvidenceGap: {
      category: components["schemas"]["GapType"];
      /** Description */
      description: string;
      /** Hypothesis Ids */
      hypothesis_ids?: string[];
      /**
       * Id
       * Format: uuid
       */
      id: string;
      /**
       * Required
       * @default true
       */
      required: boolean;
      /** Resolution Source */
      resolution_source?: string | null;
      /** Signal Need Ids */
      signal_need_ids?: string[];
      /** @default OPEN */
      status: components["schemas"]["GapStatus"];
      /** Why It Matters */
      why_it_matters: string;
    };
    /** EvidenceGap */
    vehicle_platform__prediction_evidence__domain__EvidenceGap: {
      code: components["schemas"]["EvidenceGapCode"];
      /** Reason Code */
      reason_code?: string | null;
      /** Source Node Id */
      source_node_id?: string | null;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
  create_acquisition: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AcquisitionCreate"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AcquisitionCreated"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_acquisition: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        acquisition_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AcquisitionStatusResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  publish_acquisition_batch: {
    parameters: {
      query?: never;
      header?: {
        authorization?: string | null;
      };
      path: {
        acquisition_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AcquisitionBatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      202: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AcquisitionBatchAccepted"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  finalize_acquisition: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        acquisition_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AcquisitionFinalized"];
        };
      };
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_acquisition_findings: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        acquisition_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ProvisionalFindingResponse"][];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  report_acquisition_heartbeat: {
    parameters: {
      query?: never;
      header?: {
        authorization?: string | null;
      };
      path: {
        acquisition_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AcquisitionHeartbeat"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AcquisitionStatusResponse"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  stream_acquisition_live: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        acquisition_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "text/event-stream": string;
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  stop_acquisition: {
    parameters: {
      query?: never;
      header?: {
        authorization?: string | null;
      };
      path: {
        acquisition_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AcquisitionStatusResponse"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  start_synthetic_acquisition: {
    parameters: {
      query?: {
        scenario?: "boost_drop" | "missing_recommended";
      };
      header?: {
        authorization?: string | null;
      };
      path: {
        acquisition_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      202: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": {
            [key: string]: string;
          };
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  compare_configurations: {
    parameters: {
      query: {
        after_pull_ids: string[];
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnalyticsRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnalyticsResultResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  compare_pull_analytics: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnalyticsRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnalyticsResultResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  analyze_repeated_pulls: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnalyticsRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnalyticsResultResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  compare_sessions: {
    parameters: {
      query: {
        session_ids: string[];
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnalyticsRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnalyticsResultResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_vehicle_events: {
    parameters: {
      query: {
        vehicle_id: string;
        event_type?: string | null;
        limit?: number;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["DetectedEvent"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_event: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        event_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["DetectedEvent"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  catalog_api_v1_knowledge_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["KnowledgeCatalog"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_logging_objectives: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ObjectiveResponse"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_logging_recipes: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["LoggingRecipeResponse"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_logging_recipe: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        recipe_key: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["LoggingRecipeResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  preflight_logging_recipe: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        recipe_key: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["PreflightRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PreflightResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  prediction_service_anomalies: {
    parameters: {
      query?: never;
      header?: {
        "Idempotency-Key"?: string | null;
      };
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnomalyRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PredictionResponse"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  prediction_service_evidence: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        evidence_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PredictionEvidenceProjection"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  prediction_service_verify_evidence: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        evidence_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  prediction_service_next_pull: {
    parameters: {
      query?: never;
      header?: {
        "Idempotency-Key"?: string | null;
      };
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["NextPullRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PredictionResponse"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  prediction_service_receipt: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        receipt_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PredictionResponse"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  prediction_service_receipt_evidence: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        receipt_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PredictionEvidenceProjection"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  prediction_service_materialize_evidence: {
    parameters: {
      query?: never;
      header?: {
        "Idempotency-Key"?: string | null;
      };
      path: {
        receipt_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["PredictionEvidenceMaterializeRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PredictionEvidenceMaterializeResponse"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  prediction_service_versions: {
    parameters: {
      query?: {
        limit?: number;
        offset?: number;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PredictionVersionsResponse"];
        };
      };
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_pulls: {
    parameters: {
      query: {
        vehicle_id: string;
        limit?: number;
        configuration_id?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Pull"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_pull: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        pull_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Pull"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_pull_analytics: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        pull_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnalyticsRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnalyticsResultResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_sessions: {
    parameters: {
      query?: {
        vehicle_id?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["DrivingSession"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  create_session: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["SessionCreate"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["DrivingSession"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_session: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["DrivingSession"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  analyze_session: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnalysisRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnalysisResult"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_session_analytics: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnalyticsRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnalyticsResultResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  assess_session_capabilities: {
    parameters: {
      query?: {
        recipe_key?: string;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["DatasetCapabilityReport"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_session_events: {
    parameters: {
      query?: {
        event_type?: string | null;
        category?: string | null;
        severity?: string | null;
        pull_id?: string | null;
        start?: string | null;
        end?: string | null;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["DetectedEvent"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  analyze_session_events: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["EventAnalysisRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["EventAnalysisResult"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  summarize_session_events: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["EventSummary"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  import_csv: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "multipart/form-data": components["schemas"]["Body_import_csv"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ImportResult"];
        };
      };
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unsupported Media Type */
      415: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  preview_csv_import: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "multipart/form-data": components["schemas"]["Body_preview_csv_import"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["CSVImportPreview"];
        };
      };
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unsupported Media Type */
      415: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_session_pulls: {
    parameters: {
      query?: {
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Pull"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_session_segments: {
    parameters: {
      query?: {
        segment_type?: string | null;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SessionSegment"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  query_telemetry: {
    parameters: {
      query: {
        signal: string[];
        start?: string | null;
        end?: string | null;
        limit?: number;
      };
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["TelemetryWindow"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_signals: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Signal"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_vehicles: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Vehicle"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  create_vehicle: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["VehicleCreate"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Vehicle"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_vehicle: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Vehicle"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  update_vehicle: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["VehicleUpdate"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Vehicle"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  recent_api_v1_vehicles__vehicle_id__agent_runs_get: {
    parameters: {
      query?: {
        limit?: number;
      };
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AgentRun"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  ask_api_v1_vehicles__vehicle_id__agent_runs_post: {
    parameters: {
      query?: never;
      header?: {
        "X-VIP-Prediction-Agent-Capability"?: string | null;
      };
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["Ask"];
      };
    };
    responses: {
      /** @description Successful Response */
      202: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AgentRun"];
        };
      };
      /** @description Request Timeout */
      408: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_api_v1_vehicles__vehicle_id__agent_runs__run_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
        run_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AgentRun"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  audit_api_v1_vehicles__vehicle_id__agent_runs__run_id__audit_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
        run_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["RunAudit"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  cancel_api_v1_vehicles__vehicle_id__agent_runs__run_id__cancel_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
        run_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AgentRun"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  events_api_v1_vehicles__vehicle_id__agent_runs__run_id__events_get: {
    parameters: {
      query?: {
        after?: number;
      };
      header?: never;
      path: {
        vehicle_id: string;
        run_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["StreamEvent"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  stream_api_v1_vehicles__vehicle_id__agent_runs__run_id__stream_get: {
    parameters: {
      query?: {
        after?: number;
      };
      header?: never;
      path: {
        vehicle_id: string;
        run_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_configurations: {
    parameters: {
      query?: {
        effective_at?: string | null;
      };
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["VehicleConfiguration"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  create_configuration: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ConfigurationCreate"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["VehicleConfiguration"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  build_vehicle_baseline: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
        configuration_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnalyticsRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnalyticsResultResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  recent_api_v1_vehicles__vehicle_id__investigations_get: {
    parameters: {
      query?: {
        limit?: number;
      };
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationPlan"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  create_api_v1_vehicles__vehicle_id__investigations_post: {
    parameters: {
      query?: never;
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["CreateInvestigation"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationPlan"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  source_preflight_api_v1_vehicles__vehicle_id__investigations_source_preflight_post: {
    parameters: {
      query?: never;
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["RegisterSourcePreflight"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["CapabilitySnapshot"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_api_v1_vehicles__vehicle_id__investigations__investigation_id__get: {
    parameters: {
      query?: never;
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
        investigation_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationPlan"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  approve_api_v1_vehicles__vehicle_id__investigations__investigation_id__approve_post: {
    parameters: {
      query?: never;
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
        investigation_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ApprovalRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationPlan"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  cancel_api_v1_vehicles__vehicle_id__investigations__investigation_id__cancel_post: {
    parameters: {
      query?: never;
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
        investigation_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["VersionRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationPlan"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  events_api_v1_vehicles__vehicle_id__investigations__investigation_id__events_get: {
    parameters: {
      query?: {
        after?: number;
      };
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
        investigation_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationEvent"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  reanalyze_api_v1_vehicles__vehicle_id__investigations__investigation_id__reanalyze_post: {
    parameters: {
      query?: never;
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
        investigation_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationPlan"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  refresh_api_v1_vehicles__vehicle_id__investigations__investigation_id__refresh_post: {
    parameters: {
      query?: never;
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
        investigation_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["VersionRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationPlan"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  reject_api_v1_vehicles__vehicle_id__investigations__investigation_id__reject_post: {
    parameters: {
      query?: never;
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
        investigation_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["VersionRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationPlan"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  link_session_api_v1_vehicles__vehicle_id__investigations__investigation_id__sessions_post: {
    parameters: {
      query?: never;
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
        investigation_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["LinkSessionRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InvestigationPlan"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  stream_api_v1_vehicles__vehicle_id__investigations__investigation_id__stream_get: {
    parameters: {
      query?: {
        after?: number;
      };
      header?: {
        "x-investigation-token"?: string | null;
      };
      path: {
        vehicle_id: string;
        investigation_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": unknown;
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  search_api_v1_vehicles__vehicle_id__knowledge_query_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["KnowledgeQuery"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["RetrievalResult"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  retrieval_api_v1_vehicles__vehicle_id__knowledge_retrievals__retrieval_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
        retrieval_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["RetrievalResult"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  list_modifications: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Modification"][];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  create_modification: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ModificationCreate"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Modification"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  get_vehicle_trends: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        vehicle_id: string;
        metric: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnalyticsRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnalyticsResultResponse"];
        };
      };
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  health_live: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Health"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  health_ready: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Ready"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
  version: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Version"];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorResponse"];
        };
      };
    };
  };
}
