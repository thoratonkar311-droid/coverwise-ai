from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.policy import PolicySummaryResponse
from app.schemas.policy_analysis import AnalysisDetailResponse
from app.schemas.simulation import SimulationResponse


class DashboardStats(BaseModel):
    """Aggregate statistics for the CoverWise AI analytics dashboard."""

    total_policies: int = Field(default=0, description="Total registered policy documents")
    total_analyses: int = Field(default=0, description="Total coverage analyses conducted")
    total_simulations: int = Field(default=0, description="Total cost simulations performed")
    total_treatments: int = Field(default=0, description="Total medical procedures cataloged")
    average_insurance_coverage_pct: float = Field(default=0.0, description="Average estimated insurance payout percentage")
    total_claim_amount_simulated: float = Field(default=0.0, description="Sum total of all hospital quotes simulated")
    total_estimated_savings: float = Field(default=0.0, description="Sum total of estimated insurance savings for patients")


class DashboardResponse(BaseModel):
    """Full operational summary payload for Member 1's frontend dashboard."""

    model_config = ConfigDict(from_attributes=True)

    stats: DashboardStats
    recent_policies: List[PolicySummaryResponse] = Field(default_factory=list)
    recent_analyses: List[AnalysisDetailResponse] = Field(default_factory=list)
    recent_simulations: List[SimulationResponse] = Field(default_factory=list)
    system_status: str = Field(default="operational", description="Backend service health state")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
