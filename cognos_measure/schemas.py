"""Data schemas for experiments, results, and evidence chains.

Follows the entity model from docs/articles/data-schemas.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Status(str, Enum):
    DESIGNED = "designed"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class EvidenceLevel(str, Enum):
    """Strength of evidence, from weakest to strongest."""
    ANECDOTAL = "anecdotal"          # Single observation, no controls
    OBSERVATIONAL = "observational"  # Systematic measurement, no manipulation
    COMPARATIVE = "comparative"      # Before/after or cross-condition comparison
    CONTROLLED = "controlled"        # Manipulation with controls
    REPLICATED = "replicated"        # Independently reproduced


class Measurement(BaseModel):
    """A single measured value with provenance."""
    name: str
    value: float | int | str
    unit: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = ""  # file path, git commit, API call, etc.
    notes: str = ""


class ExperimentResult(BaseModel):
    """Output of a single experiment run."""
    experiment_id: str
    run_id: str = Field(default_factory=lambda: datetime.utcnow().strftime("%Y%m%d-%H%M%S"))
    hypothesis: str
    status: Status = Status.DESIGNED
    measurements: list[Measurement] = Field(default_factory=list)
    evidence_level: EvidenceLevel = EvidenceLevel.OBSERVATIONAL
    interpretation: str = ""
    caveats: list[str] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)  # name -> file path
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add(self, name: str, value: float | int | str, **kwargs: Any) -> Measurement:
        m = Measurement(name=name, value=value, **kwargs)
        self.measurements.append(m)
        return m

    def get(self, name: str) -> Measurement | None:
        for m in self.measurements:
            if m.name == name:
                return m
        return None

    def summary(self) -> dict[str, Any]:
        return {
            "experiment": self.experiment_id,
            "run": self.run_id,
            "status": self.status.value,
            "evidence_level": self.evidence_level.value,
            "measurements": {m.name: m.value for m in self.measurements},
            "interpretation": self.interpretation,
            "caveats": self.caveats,
        }


class EvidenceChain(BaseModel):
    """Links experiment results to article claims."""
    claim_id: str          # e.g. "L2a", "H-1.2", "C2.1"
    claim_text: str
    article: str           # e.g. "Article 2"
    supporting_results: list[str] = Field(default_factory=list)  # ExperimentResult.experiment_id
    evidence_level: EvidenceLevel = EvidenceLevel.ANECDOTAL
    gaps: list[str] = Field(default_factory=list)
