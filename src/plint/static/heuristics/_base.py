"""Base class for static heuristic rules."""

from __future__ import annotations

from abc import ABC, abstractmethod

from plint.core.artifacts import AgentBundle
from plint.core.config import Config
from plint.core.findings import Finding


class Rule(ABC):
    id: str = ""
    default_severity: str = "warn"

    @abstractmethod
    def check(self, bundle: AgentBundle, config: Config) -> list[Finding]: ...
