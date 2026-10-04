from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import settings
from app.api.routes.auth import bearer, get_auth
from app.schemas.clinical import (
    AnalysisCreate, PatientCreate, PatientUpdate, ReportCreate, ReportUpdate,
    ResearchCreate, ResearchUpdate, ReviewUpdate, SignReportRequest,
)
from app.services.api_keys import SessionLocal
from app.services.auth import require_roles
from app.services.clinical_store import (
    AuditEvent, ClinicalAnalysis, ClinicalReport, Patient, ResearchRecord,
    analysis_dict, audit, init_clinical_store, now, patient_dict, report_dict, research_dict,
)

router = APIRouter(prefix="/api/v1/clinical", tags=["clinical workspace"])


def require_admin(x_admin_key: str | None) -> str:
    if not settings.api_key_admin_secret or x_admin_key != settings.api_key_admin_secret:
        raise HTTPException(status_code=401, detail="Administrator secret is required")
    return "administrator"


def context(
    credentials: HTTPAuthorizationCredentials | None,
    x_admin_key: str | None,
) -> tuple[str, int | None, str | None]:
    """Bearer auth scopes data to an organization; platform admin remains a global break-glass path."""
    if credentials:
        auth = get_auth(credentials)
        return f"user:{auth['user_id']}", auth["organization_id"], auth["role"]
    return require_admin(x_admin_key), None, None


def allowed(role: str | None, *roles: str) -> None:
    if role is not None:
        require_roles({"role": role}, *roles)


def org_filter(query, model, organization_id: int | None):
    if organization_id is not None:
        query = query.filter(model.organization_id == organization_id)
    return query


def get_patient(db, patient_id: int, organization_id: int | None):
    p = db.get(Patient, patient_id)
    if not p or (organization_id is not None and p.organization_id != organization_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return p


def get_analysis(db, analysis_id: int, organization_id: int | None):
    a = db.get(ClinicalAnalysis, analysis_id)
    if not a or (organization_id is not None and a.organization_id != organization_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    return a


def get_report(db, report_id: int, organization_id: int | None):
    r = db.get(ClinicalReport, report_id)
    if not r or (organization_id is not None and r.organization_id != organization_id):
        raise HTTPException(status_code=404, detail="Report not found")
    return r


def get_research(db, research_id: int, organization_id: int | None):
    r = db.get(ResearchRecord, research_id)
    if not r or (organization_id is not None and r.organization_id != organization_id):
        raise HTTPException(status_code=404, detail="Research record not found")
    return r


@router.get("/patients")
def list_patients(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> list[dict]:
    actor, org_id, _ = context(credentials, x_admin_key)
    init_clinical_store()
    with SessionLocal() as db:
        q = org_filter(db.query(Patient), Patient, org_id)
        return [patient_dict(p) for p in q.order_by(Patient.id.desc()).all()]


@router.post("/patients")
def create_patient(
    payload: PatientCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, role = context(credentials, x_admin_key)
    allowed(role, "owner", "admin", "doctor", "radiologist", "dermatologist", "nurse", "staff")
    init_clinical_store()
    with SessionLocal() as db:
        if org_id is not None and db.query(Patient).filter(
            Patient.organization_id == org_id, Patient.patient_ref == payload.patient_ref.strip()
        ).first():
            raise HTTPException(status_code=409, detail="Patient reference already exists")
        p = Patient(organization_id=org_id, patient_ref=payload.patient_ref.strip(), name=payload.name.strip(),
                    date_of_birth=payload.date_of_birth, sex=payload.sex, notes=payload.notes,
                    created_at=now(), updated_at=now())
        db.add(p)
        try:
            db.commit(); db.refresh(p)
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="Patient could not be created") from exc
        result = patient_dict(p)
    audit("patient.created", "patient", result["id"], actor, result["patient_ref"], org_id)
    return result


@router.patch("/patients/{patient_id}")
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, role = context(credentials, x_admin_key)
    allowed(role, "owner", "admin", "doctor", "radiologist", "dermatologist", "nurse", "staff")
    init_clinical_store()
    with SessionLocal() as db:
        p = get_patient(db, patient_id, org_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(p, key, value)
        p.updated_at = now(); db.commit(); db.refresh(p); result = patient_dict(p)
    audit("patient.updated", "patient", patient_id, actor, organization_id=org_id)
    return result


@router.get("/analyses")
def list_analyses(
    patient_id: int | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> list[dict]:
    actor, org_id, _ = context(credentials, x_admin_key)
    init_clinical_store()
    with SessionLocal() as db:
        q = org_filter(db.query(ClinicalAnalysis), ClinicalAnalysis, org_id)
        if patient_id is not None:
            q = q.filter(ClinicalAnalysis.patient_id == patient_id)
        return [analysis_dict(a) for a in q.order_by(ClinicalAnalysis.id.desc()).all()]


@router.post("/analyses")
def create_analysis(
    payload: AnalysisCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, role = context(credentials, x_admin_key)
    allowed(role, "owner", "admin", "doctor", "radiologist", "dermatologist", "nurse", "staff")
    init_clinical_store()
    if payload.image_type not in {"xray", "skin"}:
        raise HTTPException(status_code=400, detail="Invalid image type")
    with SessionLocal() as db:
        if payload.patient_id is not None:
            patient = get_patient(db, payload.patient_id, org_id)
            if org_id is not None and patient.organization_id != org_id:
                raise HTTPException(status_code=404, detail="Patient not found")
        a = ClinicalAnalysis(organization_id=org_id, **payload.model_dump(), status="pending_review", created_at=now())
        db.add(a); db.commit(); db.refresh(a); result = analysis_dict(a)
    audit("analysis.created", "analysis", result["id"], actor, result["finding"], org_id)
    return result


@router.post("/analyses/{analysis_id}/review")
def review_analysis(
    analysis_id: int,
    payload: ReviewUpdate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, role = context(credentials, x_admin_key)
    allowed(role, "owner", "admin", "doctor", "radiologist", "dermatologist")
    init_clinical_store()
    with SessionLocal() as db:
        a = get_analysis(db, analysis_id, org_id)
        a.status = payload.status; a.reviewer = payload.reviewer.strip()
        a.reviewer_note = payload.note; a.reviewed_at = now()
        db.commit(); db.refresh(a); result = analysis_dict(a)
    audit("analysis.reviewed", "analysis", analysis_id, actor, payload.status, org_id)
    return result


@router.get("/reports")
def list_reports(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> list[dict]:
    actor, org_id, _ = context(credentials, x_admin_key)
    init_clinical_store()
    with SessionLocal() as db:
        q = org_filter(db.query(ClinicalReport), ClinicalReport, org_id)
        return [report_dict(r) for r in q.order_by(ClinicalReport.id.desc()).all()]


@router.post("/reports")
def create_report(
    payload: ReportCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, role = context(credentials, x_admin_key)
    allowed(role, "owner", "admin", "doctor", "radiologist", "dermatologist")
    init_clinical_store()
    with SessionLocal() as db:
        analysis = get_analysis(db, payload.analysis_id, org_id)
        t = now()
        r = ClinicalReport(organization_id=org_id, **payload.model_dump(), status="draft", created_at=t, updated_at=t)
        db.add(r); db.commit(); db.refresh(r); result = report_dict(r)
    audit("report.created", "report", result["id"], actor, f"analysis:{analysis.id}", org_id)
    return result


@router.patch("/reports/{report_id}")
def update_report(
    report_id: int,
    payload: ReportUpdate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, role = context(credentials, x_admin_key)
    allowed(role, "owner", "admin", "doctor", "radiologist", "dermatologist")
    init_clinical_store()
    with SessionLocal() as db:
        r = get_report(db, report_id, org_id)
        if r.status == "signed":
            raise HTTPException(status_code=409, detail="Signed reports are immutable")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(r, key, value)
        r.updated_at = now(); db.commit(); db.refresh(r); result = report_dict(r)
    audit("report.updated", "report", report_id, actor, organization_id=org_id)
    return result


@router.post("/reports/{report_id}/sign")
def sign_report(
    report_id: int,
    payload: SignReportRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, role = context(credentials, x_admin_key)
    allowed(role, "owner", "admin", "doctor", "radiologist", "dermatologist")
    init_clinical_store()
    with SessionLocal() as db:
        r = get_report(db, report_id, org_id)
        if r.status == "signed":
            raise HTTPException(status_code=409, detail="Report is already signed")
        r.status = "signed"; r.signed_by = payload.signer.strip(); r.signed_at = now(); r.updated_at = now()
        db.commit(); db.refresh(r); result = report_dict(r)
    audit("report.signed", "report", report_id, actor, payload.signer, org_id)
    return result


@router.get("/research")
def list_research(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> list[dict]:
    actor, org_id, _ = context(credentials, x_admin_key)
    init_clinical_store()
    with SessionLocal() as db:
        q = org_filter(db.query(ResearchRecord), ResearchRecord, org_id)
        return [research_dict(r) for r in q.order_by(ResearchRecord.id.desc()).all()]


@router.post("/research")
def create_research(
    payload: ResearchCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, role = context(credentials, x_admin_key)
    allowed(role, "owner", "admin", "researcher", "doctor")
    init_clinical_store()
    with SessionLocal() as db:
        t = now()
        r = ResearchRecord(organization_id=org_id, **payload.model_dump(), created_at=t, updated_at=t)
        db.add(r); db.commit(); db.refresh(r); result = research_dict(r)
    audit("research.created", "research", result["id"], actor, result["title"], org_id)
    return result


@router.patch("/research/{research_id}")
def update_research(
    research_id: int,
    payload: ResearchUpdate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, role = context(credentials, x_admin_key)
    allowed(role, "owner", "admin", "researcher", "doctor")
    init_clinical_store()
    with SessionLocal() as db:
        r = get_research(db, research_id, org_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(r, key, value)
        r.updated_at = now(); db.commit(); db.refresh(r); result = research_dict(r)
    audit("research.updated", "research", research_id, actor, organization_id=org_id)
    return result


@router.get("/audit")
def list_audit(
    limit: int = 100,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> list[dict]:
    actor, org_id, _ = context(credentials, x_admin_key)
    init_clinical_store()
    limit = max(1, min(limit, 500))
    with SessionLocal() as db:
        q = org_filter(db.query(AuditEvent), AuditEvent, org_id)
        rows = q.order_by(AuditEvent.id.desc()).limit(limit).all()
        return [{"id": e.id, "organization_id": e.organization_id, "event_type": e.event_type,
                 "entity_type": e.entity_type, "entity_id": e.entity_id, "actor": e.actor,
                 "details": e.details, "created_at": e.created_at.isoformat()} for e in rows]


@router.get("/analytics")
def analytics(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_admin_key: str | None = Header(default=None),
) -> dict:
    actor, org_id, _ = context(credentials, x_admin_key)
    init_clinical_store()
    with SessionLocal() as db:
        aq = org_filter(db.query(ClinicalAnalysis), ClinicalAnalysis, org_id)
        rq = org_filter(db.query(ClinicalReport), ClinicalReport, org_id)
        pq = org_filter(db.query(Patient), Patient, org_id)
        resq = org_filter(db.query(ResearchRecord), ResearchRecord, org_id)
        analyses = aq.all()
        reports = rq.all()
        patients = pq.count()
        research = resq.count()
        reviewed = sum(1 for a in analyses if a.status == "reviewed")
        pending = sum(1 for a in analyses if a.status == "pending_review")
        signed = sum(1 for r in reports if r.status == "signed")
        avg_conf = sum(a.confidence for a in analyses) / len(analyses) if analyses else 0
        audit_count = org_filter(db.query(AuditEvent), AuditEvent, org_id).count()
        return {"patients": patients, "analyses": len(analyses), "reviewed_analyses": reviewed,
                "pending_reviews": pending, "reports": len(reports), "signed_reports": signed,
                "research_records": research, "average_confidence": round(avg_conf, 4),
                "audit_events": audit_count}
