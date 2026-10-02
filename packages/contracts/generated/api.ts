export interface paths {
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
    /** Body_import_csv */
    Body_import_csv: {
      /** File */
      file: string;
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
    /** HTTPValidationError */
    HTTPValidationError: {
      /** Detail */
      detail?: components["schemas"]["ValidationError"][];
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
    /** ValidationError */
    ValidationError: {
      /** Context */
      ctx?: Record<string, never>;
      /** Input */
      input?: unknown;
      /** Location */
      loc: (string | number)[];
      /** Message */
      msg: string;
      /** Error Type */
      type: string;
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Internal Server Error */
      500: {
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
      /** @description Internal Server Error */
      500: {
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
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
      /** @description Internal Server Error */
      500: {
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
      /** @description Internal Server Error */
      500: {
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
