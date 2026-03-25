"""Domain enums."""

from enum import Enum


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
