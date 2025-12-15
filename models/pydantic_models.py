from pydantic import BaseModel, Field, validator
from typing import List, Dict
from datetime import datetime


class CaseModel(BaseModel):
    case_id: str
    title: str
    facts: str

    @validator("case_id", "title", "facts")
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class ArgumentModel(BaseModel):
    debate_id: str
    agent: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @validator("agent")
    def valid_agent(cls, v):
        if v not in ("prosecutor", "defense", "witness"):
            raise ValueError("Invalid agent type")
        return v


class JudgementModel(BaseModel):
    judgement_id: str
    case_id: str
    verdict: str
    prosecution_score: float
    defense_score: float
    rubric_scores: Dict[str, float]
    reasoning: str
    case_facts: str
    evidence_considered: List[Dict]
    hearing_log: List[Dict]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @validator("prosecution_score", "defense_score")
    def score_range(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v
