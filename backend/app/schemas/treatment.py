from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TreatmentBase(BaseModel):
    """Base fields for medical treatment and standard cost benchmarking."""

    name: str = Field(..., min_length=1, max_length=255, description="Medical procedure or treatment name")
    category: Optional[str] = Field(None, max_length=100, description="Department or clinical category")
    description: Optional[str] = Field(None, description="Clinical summary and details")
    typical_cost_min: Optional[float] = Field(None, ge=0.0, description="Minimum typical benchmark cost")
    typical_cost_max: Optional[float] = Field(None, ge=0.0, description="Maximum typical benchmark cost")


class TreatmentCreate(TreatmentBase):
    """Schema for adding a new treatment to the catalog."""

    pass


class TreatmentResponse(TreatmentBase):
    """API response model for treatment catalog entries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
