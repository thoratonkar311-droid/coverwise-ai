from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.coverage_rule import CoverageRuleResponse


class PolicyBase(BaseModel):
    """Base fields for an insurance policy document."""

    filename: str = Field(..., max_length=255, description="Original policy filename")
    policy_number: Optional[str] = Field(None, max_length=100, description="Extracted policy number")
    insurer_name: Optional[str] = Field(None, max_length=255, description="Insurance provider/company name")
    plan_name: Optional[str] = Field(None, max_length=255, description="Policy plan or product name")
    policy_holder_name: Optional[str] = Field(None, max_length=255, description="Insured person/holder name")
    status: str = Field(default="uploaded", max_length=50, description="Processing status")


class PolicyCreate(PolicyBase):
    """Payload for creating or registering an uploaded policy."""

    user_id: Optional[str] = Field(None, max_length=100, description="User identifier when auth is active")
    file_path: Optional[str] = Field(None, max_length=500, description="Storage location on disk or object store")
    raw_metadata: Optional[Any] = Field(None, description="Arbitrary raw metadata from document parser")


class PolicyUpdate(BaseModel):
    """Payload for updating policy status or extracted metadata."""

    policy_number: Optional[str] = None
    insurer_name: Optional[str] = None
    plan_name: Optional[str] = None
    policy_holder_name: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    raw_metadata: Optional[Any] = None


class PolicySummaryResponse(BaseModel):
    """Lightweight summary model for dashboard listings."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    policy_number: Optional[str] = None
    insurer_name: Optional[str] = None
    plan_name: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class PolicyResponse(PolicyBase):
    """Detailed policy response including rules and extraction metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[str] = None
    file_path: Optional[str] = None
    raw_metadata: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    coverage_rules: List[CoverageRuleResponse] = []


class PolicyUploadResponse(BaseModel):
    """Response returned upon successful policy file upload."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique ID of created policy record")
    filename: str = Field(..., description="Uploaded file name")
    status: str = Field(..., description="Processing status, e.g. uploaded, processing")
    message: str = Field(default="Policy document uploaded successfully.", description="Status message")

