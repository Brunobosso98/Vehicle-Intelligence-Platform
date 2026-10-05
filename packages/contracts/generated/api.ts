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
    /** Health */
    Health: {
      /**
       * Status
       * @default ok
       * @constant
       */
      status: "ok";
    };
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
    /** ObjectiveResponse */
    ObjectiveResponse: {
      /** Key */
      key: string;
      /** Recipe Key */
      recipe_key: string;
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
