#!/usr/bin/env bash

# Poll an HTTP endpoint until it returns the expected status, retaining the last response body.
# Usage: wait_http_status URL EXPECTED_STATUS OUTPUT_FILE [TIMEOUT_SECONDS] [INTERVAL_SECONDS]
wait_http_status() {
  local url=$1
  local expected_status=$2
  local output=$3
  local timeout=${4:-60}
  local interval=${5:-2}
  local deadline=$((SECONDS + timeout))
  local status
  local temporary="${output}.tmp"

  mkdir -p "$(dirname "$output")"
  while ((SECONDS < deadline)); do
    if ! status=$(curl -sS -o "$temporary" -w '%{http_code}' "$url"); then
      status=unavailable
    fi
    if [[ "$status" == "$expected_status" ]]; then
      mv "$temporary" "$output"
      return 0
    fi
    sleep "$interval"
  done

  [[ ! -f "$temporary" ]] || mv "$temporary" "$output"
  echo "Timed out after ${timeout}s waiting for HTTP ${expected_status} from ${url}; last status: ${status:-unavailable}" >&2
  return 1
}
