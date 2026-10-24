"""Pydantic schemas for all DeepDive data structures."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────

class RunState(str, Enum):
    START = "START"
    PLAN = "PLAN"
    SEARCH = "SEARCH"
    RETRIEVE = "RETRIEVE"
    EXTRACT_EVIDENCE = "EXTRACT_EVIDENCE"
    SCORE_SOURCES = "SCORE_SOURCES"
    DRAFT_ATOMIC_CLAIMS = "DRAFT_ATOMIC_CLAIMS"
    CLAIM_COURTROOM = "CLAIM_COURTROOM"
    DETECT_CONTRADICTIONS = "DETECT_CONTRADICTIONS"
    MEASURE_COVERAGE = "MEASURE_COVERAGE"
    RESEARCH_GAPS = "RESEARCH_GAPS"
    SYNTHESIZE = "SYNTHESIZE"
    VERIFY_FINAL_REPORT = "VERIFY_FINAL_REPORT"
    EXPORT = "EXPORT"
    END = "END"
    FAILED = "FAILED"


class ClaimVerdict(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"


class CoverageStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class ContradictionType(str, Enum):
    NUMERIC = "numeric"
    DATE = "date"
    DEFINITION = "definition"
    CAUSAL = "causal"
    FORECAST = "forecast"
    SCOPE = "scope"


class ContradictionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ContradictionResolution(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CONTEXT_DEPENDENT = "context-dependent"


# ── Core Data ──────────────────────────────────────────────────────────

def _id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class SubQuestion(BaseModel):
    id: str = Field(default_factory=_id)
    text: str
    completion_criteria: str = ""
    parent_question: str = ""


class SearchQuery(BaseModel):
    id: str = Field(default_factory=_id)
    subquestion_id: str
    query: str
    source_preference: str = ""


class Source(BaseModel):
    id: str = Field(default_factory=_id)
    url: str
    title: str = ""
    retrieved_at: str = Field(default_factory=_now)
    content_hash: str = ""
    content_snippet: str = ""
    # Exact sanitized/truncated retrieval snapshot; absent on historical records.
    content_snapshot: Optional[str] = None
    trust_score: float = 0.0
    trust_factors: dict = Field(default_factory=dict)


class Evidence(BaseModel):
    id: str = Field(default_factory=_id)
    source_id: str
    subquestion_id: str = ""
    passage: str
    passage_hash: str = ""
    source_snapshot_hash: str = ""
    relevance: float = 0.0

    def compute_hash(self) -> None:
        self.passage_hash = _hash(self.passage)


class AtomicClaim(BaseModel):
    id: str = Field(default_factory=_id)
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    subquestion_id: str = ""


class ProsecutorArgument(BaseModel):
    claim_id: str
    weaknesses: list[str] = Field(default_factory=list)
    unsupported_components: list[str] = Field(default_factory=list)


class DefenseArgument(BaseModel):
    claim_id: str
    supporting_passages: list[dict] = Field(default_factory=list)
    # Each: {"evidence_id": str, "passage_excerpt": str, "supports_component": str}


class ClaimJudgement(BaseModel):
    claim_id: str
    verdict: ClaimVerdict
    confidence: float = 0.0
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    missing_evidence: str = ""
    recommended_action: str = ""


class Contradiction(BaseModel):
    id: str = Field(default_factory=_id)
    topic: str
    claim_a: str
    claim_b: str
    evidence_a: list[str] = Field(default_factory=list)
    evidence_b: list[str] = Field(default_factory=list)
    type: ContradictionType = ContradictionType.DEFINITION
    severity: ContradictionSeverity = ContradictionSeverity.MEDIUM
    resolution: ContradictionResolution = ContradictionResolution.UNRESOLVED
    explanation: str = ""


class CoverageEntry(BaseModel):
    subquestion_id: str
    subquestion_text: str = ""
    evidence_count: int = 0
    source_count: int = 0
    primary_source_count: int = 0
    verified_claim_count: int = 0
    contradiction_count: int = 0
    coverage_score: float = 0.0
    status: CoverageStatus = CoverageStatus.RED


class StateTransition(BaseModel):
    from_state: RunState
    to_state: RunState
    timestamp: str = Field(default_factory=_now)
    reason: str = ""


class AgentCall(BaseModel):
    id: str = Field(default_factory=_id)
    agent: str
    model: str = ""
    prompt_version: str = ""
    timestamp: str = Field(default_factory=_now)
    input_hash: str = ""
    output_hash: str = ""
    duration_ms: int = 0
    success: bool = True
    finish_reason: str = ""
    error: str = ""
    response_preview: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class VerificationCertificate(BaseModel):
    run_id: str
    original_question: str
    execution_timestamp: str = Field(default_factory=_now)
    mesh_models_used: list[str] = Field(default_factory=list)
    source_count: int = 0
    evidence_count: int = 0
    drafted_claim_count: int = 0
    supported_claim_count: int = 0
    rejected_claim_count: int = 0
    contradiction_count: int = 0
    groundedness_rate: float = 0.0
    citation_coverage_rate: float = 0.0
    citation_mutation_rejection_rate: Optional[float] = None
    research_rounds: int = 0
    source_quality_distribution: dict = Field(default_factory=dict)
    prompt_versions: dict = Field(default_factory=dict)
    source_content_hashes: list[str] = Field(default_factory=list)
    evaluation_limitations: list[str] = Field(default_factory=list)


# ── Run State Container ───────────────────────────────────────────────

class ResearchRun(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    question: str
    created_at: str = Field(default_factory=_now)
    current_state: RunState = RunState.START
    research_round: int = 0
    confidence_threshold: float = 0.7
    max_rounds: int = 3

    subquestions: list[SubQuestion] = Field(default_factory=list)
    search_queries: list[SearchQuery] = Field(default_factory=list)
    search_audit: list[dict] = Field(default_factory=list)
    retrieval_audit: list[dict] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    claims: list[AtomicClaim] = Field(default_factory=list)
    claim_selection_audit: list[dict] = Field(default_factory=list)
    judgements: list[ClaimJudgement] = Field(default_factory=list)
    prosecution: list[ProsecutorArgument] = Field(default_factory=list)
    defense: list[DefenseArgument] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    contradiction_audit: list[dict] = Field(default_factory=list)
    coverage: list[CoverageEntry] = Field(default_factory=list)
    state_transitions: list[StateTransition] = Field(default_factory=list)
    agent_calls: list[AgentCall] = Field(default_factory=list)

    final_report: str = ""
    certificate: Optional[VerificationCertificate] = None
    error: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)

    def transition(self, new_state: RunState, reason: str = "") -> None:
        self.state_transitions.append(
            StateTransition(
                from_state=self.current_state,
                to_state=new_state,
                reason=reason,
            )
        )
        self.current_state = new_state

    def supported_claims(self, confidence_threshold: float = 0.0) -> list[AtomicClaim]:
        supported_ids = {
            j.claim_id for j in self.judgements
            if j.verdict == ClaimVerdict.SUPPORTED
            and j.confidence >= confidence_threshold
            and j.supporting_evidence_ids
        }
        return [c for c in self.claims if c.id in supported_ids]

    def get_evidence_by_id(self, eid: str) -> Optional[Evidence]:
        for e in self.evidence:
            if e.id == eid:
                return e
        return None

    def get_source_by_id(self, sid: str) -> Optional[Source]:
        for s in self.sources:
            if s.id == sid:
                return s
        return None


# ── API Request/Response ──────────────────────────────────────────────

class ResearchRequest(BaseModel):
    question: str = Field(min_length=10, max_length=2000)
    source_urls: list[str] = Field(default_factory=list, max_length=20)
    max_rounds: Optional[int] = Field(default=None, ge=1, le=5)
    confidence_threshold: Optional[float] = Field(default=None, ge=0.5, le=1.0)


class FollowUpRequest(ResearchRequest):
    pass


class HealthResponse(BaseModel):
    status: str = "ok"
    mesh_configured: bool = False
    database: str = ""
    version: str = "1.0.0"
    db_ok: bool = False


class RunSummary(BaseModel):
    id: str
    question: str
    state: RunState
    created_at: str
    source_count: int = 0
    claim_count: int = 0
    supported_claim_count: int = 0
    contradiction_count: int = 0
    research_rounds: int = 0
    error: Optional[str] = None
