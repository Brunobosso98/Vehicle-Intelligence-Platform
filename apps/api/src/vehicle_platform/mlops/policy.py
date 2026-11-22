"""Environment and execution fences for the offline control plane."""

import os
from typing import Literal


def require_controlled_environment() -> Literal["development", "test"]:
    environment = os.environ.get("ENVIRONMENT")
    if environment == "development":
        return "development"
    if environment == "test":
        return "test"
    raise RuntimeError("MLOps requires an explicitly configured development or test environment")
