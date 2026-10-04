from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    patient_ref: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    date_of_birth: str | None = None
    sex: str | None = None
    notes: str | None = None


class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    date_of_birth: str | None = None
    sex: str | None = None
    notes: str | None = None


class AnalysisCreate(BaseModel):
    patient_id: int | None = None
    image_type: str
    source_filename: str | None = None
    finding: str
    confidence: float = Field(ge=0, le=1)
    needs_review: bool = True
    model_name: str | None = None
    model_source: str | None = None
    research_status: str = "research_only_not_clinically_validated"


class ReviewUpdate(BaseModel):
    status: str = Field(pattern="^(pending_review|reviewed|rejected)$")
    reviewer: str = Field(min_length=2, max_length=255)
    note: str | None = None


class ReportCreate(BaseModel):
    analysis_id: int
    title: str = Field(min_length=2, max_length=255)
    impression: str = Field(min_length=2)
    findings: str = Field(min_length=2)
    author: str = Field(min_length=2, max_length=255)


class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    impression: str | None = Field(default=None, min_length=2)
    findings: str | None = Field(default=None, min_length=2)


class SignReportRequest(BaseModel):
    signer: str = Field(min_length=2, max_length=255)


class ResearchCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    dataset: str | None = None
    hypothesis: str | None = None
    model_name: str | None = None
    metric_summary: str | None = None
    status: str = "draft"
    owner: str = Field(min_length=2, max_length=255)


class ResearchUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    dataset: str | None = None
    hypothesis: str | None = None
    model_name: str | None = None
    metric_summary: str | None = None
    status: str | None = None
