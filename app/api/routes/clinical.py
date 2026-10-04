from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.schemas.clinical import (
    AnalysisCreate, PatientCreate, PatientUpdate, ReportCreate, ReportUpdate,
    ResearchCreate, ResearchUpdate, ReviewUpdate, SignReportRequest,
)
from app.services.api_keys import SessionLocal
from app.services.clinical_store import (
    AuditEvent, ClinicalAnalysis, ClinicalReport, Patient, ResearchRecord,
    analysis_dict, audit, init_clinical_store, now, patient_dict, report_dict, research_dict,
)

router = APIRouter(prefix="/api/v1/clinical", tags=["clinical workspace"])


def require_admin(x_admin_key: str | None) -> str:
    if not settings.api_key_admin_secret or x_admin_key != settings.api_key_admin_secret:
        raise HTTPException(status_code=401, detail="Administrator secret is required")
    return "administrator"


@router.get("/patients")
def list_patients(x_admin_key: str | None = Header(default=None)) -> list[dict]:
    actor = require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        return [patient_dict(p) for p in db.query(Patient).order_by(Patient.id.desc()).all()]


@router.post("/patients")
def create_patient(payload: PatientCreate, x_admin_key: str | None = Header(default=None)) -> dict:
    actor = require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        p = Patient(patient_ref=payload.patient_ref.strip(), name=payload.name.strip(),
                    date_of_birth=payload.date_of_birth, sex=payload.sex, notes=payload.notes,
                    created_at=now(), updated_at=now())
        db.add(p)
        try:
            db.commit(); db.refresh(p)
        except Exception as exc:
            db.rollback(); raise HTTPException(status_code=409, detail="Patient reference already exists") from exc
        result = patient_dict(p)
    audit("patient.created", "patient", result["id"], actor, result["patient_ref"])
    return result


@router.patch("/patients/{patient_id}")
def update_patient(patient_id: int, payload: PatientUpdate, x_admin_key: str | None = Header(default=None)) -> dict:
    actor = require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        p = db.get(Patient, patient_id)
        if not p: raise HTTPException(status_code=404, detail="Patient not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(p, key, value)
        p.updated_at = now(); db.commit(); db.refresh(p); result = patient_dict(p)
    audit("patient.updated", "patient", patient_id, actor)
    return result


@router.get("/analyses")
def list_analyses(x_admin_key: str | None = Header(default=None), patient_id: int | None = None) -> list[dict]:
    actor = require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        q = db.query(ClinicalAnalysis)
        if patient_id is not None: q = q.filter(ClinicalAnalysis.patient_id == patient_id)
        return [analysis_dict(a) for a in q.order_by(ClinicalAnalysis.id.desc()).all()]


@router.post("/analyses")
def create_analysis(payload: AnalysisCreate, x_admin_key: str | None = Header(default=None)) -> dict:
    actor = require_admin(x_admin_key); init_clinical_store()
    if payload.image_type not in {"xray", "skin"}: raise HTTPException(status_code=400, detail="Invalid image type")
    with SessionLocal() as db:
        if payload.patient_id and not db.get(Patient, payload.patient_id):
            raise HTTPException(status_code=404, detail="Patient not found")
        a = ClinicalAnalysis(**payload.model_dump(), status="pending_review", created_at=now())
        db.add(a); db.commit(); db.refresh(a); result = analysis_dict(a)
    audit("analysis.created", "analysis", result["id"], actor, result["finding"])
    return result


@router.post("/analyses/{analysis_id}/review")
def review_analysis(analysis_id: int, payload: ReviewUpdate, x_admin_key: str | None = Header(default=None)) -> dict:
    actor = require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        a = db.get(ClinicalAnalysis, analysis_id)
        if not a: raise HTTPException(status_code=404, detail="Analysis not found")
        a.status = payload.status; a.reviewer = payload.reviewer.strip()
        a.reviewer_note = payload.note; a.reviewed_at = now()
        db.commit(); db.refresh(a); result = analysis_dict(a)
    audit("analysis.reviewed", "analysis", analysis_id, payload.reviewer, payload.status)
    return result


@router.get("/reports")
def list_reports(x_admin_key: str | None = Header(default=None)) -> list[dict]:
    actor = require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        return [report_dict(r) for r in db.query(ClinicalReport).order_by(ClinicalReport.id.desc()).all()]


@router.post("/reports")
def create_report(payload: ReportCreate, x_admin_key: str | None = Header(default=None)) -> dict:
    actor = require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        if not db.get(ClinicalAnalysis, payload.analysis_id): raise HTTPException(status_code=404, detail="Analysis not found")
        t=now(); r=ClinicalReport(**payload.model_dump(), status="draft", created_at=t, updated_at=t)
        db.add(r); db.commit(); db.refresh(r); result=report_dict(r)
    audit("report.created", "report", result["id"], actor)
    return result


@router.patch("/reports/{report_id}")
def update_report(report_id: int, payload: ReportUpdate, x_admin_key: str | None = Header(default=None)) -> dict:
    actor = require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        r=db.get(ClinicalReport, report_id)
        if not r: raise HTTPException(status_code=404, detail="Report not found")
        if r.status == "signed": raise HTTPException(status_code=409, detail="Signed reports are immutable")
        for key,value in payload.model_dump(exclude_unset=True).items(): setattr(r,key,value)
        r.updated_at=now(); db.commit(); db.refresh(r); result=report_dict(r)
    audit("report.updated", "report", report_id, actor)
    return result


@router.post("/reports/{report_id}/sign")
def sign_report(report_id: int, payload: SignReportRequest, x_admin_key: str | None = Header(default=None)) -> dict:
    actor = require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        r=db.get(ClinicalReport, report_id)
        if not r: raise HTTPException(status_code=404, detail="Report not found")
        if r.status == "signed": raise HTTPException(status_code=409, detail="Report is already signed")
        r.status="signed"; r.signed_by=payload.signer.strip(); r.signed_at=now(); r.updated_at=now()
        db.commit(); db.refresh(r); result=report_dict(r)
    audit("report.signed", "report", report_id, payload.signer)
    return result


@router.get("/research")
def list_research(x_admin_key: str | None = Header(default=None)) -> list[dict]:
    actor=require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        return [research_dict(r) for r in db.query(ResearchRecord).order_by(ResearchRecord.id.desc()).all()]


@router.post("/research")
def create_research(payload: ResearchCreate, x_admin_key: str | None = Header(default=None)) -> dict:
    actor=require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        t=now(); r=ResearchRecord(**payload.model_dump(),created_at=t,updated_at=t)
        db.add(r); db.commit(); db.refresh(r); result=research_dict(r)
    audit("research.created","research",result["id"],actor,result["title"])
    return result


@router.patch("/research/{research_id}")
def update_research(research_id: int, payload: ResearchUpdate, x_admin_key: str | None = Header(default=None)) -> dict:
    actor=require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        r=db.get(ResearchRecord,research_id)
        if not r: raise HTTPException(status_code=404,detail="Research record not found")
        for key,value in payload.model_dump(exclude_unset=True).items(): setattr(r,key,value)
        r.updated_at=now(); db.commit(); db.refresh(r); result=research_dict(r)
    audit("research.updated","research",research_id,actor)
    return result


@router.get("/audit")
def list_audit(x_admin_key: str | None = Header(default=None), limit: int = 100) -> list[dict]:
    actor=require_admin(x_admin_key); init_clinical_store()
    limit=max(1,min(limit,500))
    with SessionLocal() as db:
        rows=db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit).all()
        return [{"id":e.id,"event_type":e.event_type,"entity_type":e.entity_type,
                 "entity_id":e.entity_id,"actor":e.actor,"details":e.details,
                 "created_at":e.created_at.isoformat()} for e in rows]


@router.get("/analytics")
def analytics(x_admin_key: str | None = Header(default=None)) -> dict:
    actor=require_admin(x_admin_key); init_clinical_store()
    with SessionLocal() as db:
        analyses=db.query(ClinicalAnalysis).all()
        reports=db.query(ClinicalReport).all()
        patients=db.query(Patient).count()
        research=db.query(ResearchRecord).count()
        reviewed=sum(1 for a in analyses if a.status=="reviewed")
        pending=sum(1 for a in analyses if a.status=="pending_review")
        signed=sum(1 for r in reports if r.status=="signed")
        avg_conf=sum(a.confidence for a in analyses)/len(analyses) if analyses else 0
        return {"patients":patients,"analyses":len(analyses),"reviewed_analyses":reviewed,
                "pending_reviews":pending,"reports":len(reports),"signed_reports":signed,
                "research_records":research,"average_confidence":round(avg_conf,4),
                "audit_events":db.query(AuditEvent).count()}
