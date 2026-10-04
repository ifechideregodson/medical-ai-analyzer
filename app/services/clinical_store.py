from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.services.api_keys import Base, SessionLocal, engine, init_api_key_store


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    patient_ref = Column(String(80), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    date_of_birth = Column(String(20), nullable=True)
    sex = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class ClinicalAnalysis(Base):
    __tablename__ = "clinical_analyses"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    image_type = Column(String(30), nullable=False)
    source_filename = Column(String(255), nullable=True)
    finding = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False)
    needs_review = Column(Boolean, nullable=False, default=True)
    model_name = Column(String(255), nullable=True)
    model_source = Column(String(255), nullable=True)
    research_status = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False, default="pending_review")
    reviewer = Column(String(255), nullable=True)
    reviewer_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class ClinicalReport(Base):
    __tablename__ = "clinical_reports"
    id = Column(Integer, primary_key=True)
    analysis_id = Column(Integer, ForeignKey("clinical_analyses.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    impression = Column(Text, nullable=False)
    findings = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="draft")
    author = Column(String(255), nullable=False)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    signed_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class ResearchRecord(Base):
    __tablename__ = "research_records"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    dataset = Column(String(255), nullable=True)
    hypothesis = Column(Text, nullable=True)
    model_name = Column(String(255), nullable=True)
    metric_summary = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="draft")
    owner = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True)
    event_type = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(80), nullable=False)
    entity_id = Column(String(80), nullable=True)
    actor = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


def now() -> datetime:
    return datetime.now(timezone.utc)


def init_clinical_store() -> None:
    init_api_key_store()
    Base.metadata.create_all(bind=engine)


def audit(event_type: str, entity_type: str, entity_id: int | str | None, actor: str, details: str = "") -> None:
    init_clinical_store()
    with SessionLocal() as db:
        db.add(AuditEvent(event_type=event_type, entity_type=entity_type,
                          entity_id=str(entity_id) if entity_id is not None else None,
                          actor=actor, details=details, created_at=now()))
        db.commit()


def patient_dict(p: Patient) -> dict[str, Any]:
    return {"id": p.id, "patient_ref": p.patient_ref, "name": p.name,
            "date_of_birth": p.date_of_birth, "sex": p.sex, "notes": p.notes,
            "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat()}


def analysis_dict(a: ClinicalAnalysis) -> dict[str, Any]:
    return {"id": a.id, "patient_id": a.patient_id, "image_type": a.image_type,
            "source_filename": a.source_filename, "finding": a.finding,
            "confidence": a.confidence, "needs_review": a.needs_review,
            "model_name": a.model_name, "model_source": a.model_source,
            "research_status": a.research_status, "status": a.status,
            "reviewer": a.reviewer, "reviewer_note": a.reviewer_note,
            "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
            "created_at": a.created_at.isoformat()}


def report_dict(r: ClinicalReport) -> dict[str, Any]:
    return {"id": r.id, "analysis_id": r.analysis_id, "title": r.title,
            "impression": r.impression, "findings": r.findings, "status": r.status,
            "author": r.author, "signed_at": r.signed_at.isoformat() if r.signed_at else None,
            "signed_by": r.signed_by, "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat()}


def research_dict(r: ResearchRecord) -> dict[str, Any]:
    return {"id": r.id, "title": r.title, "dataset": r.dataset,
            "hypothesis": r.hypothesis, "model_name": r.model_name,
            "metric_summary": r.metric_summary, "status": r.status,
            "owner": r.owner, "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat()}
