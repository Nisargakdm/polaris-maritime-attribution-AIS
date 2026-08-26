from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse, HTMLResponse
from app.models.schemas import InvestigationDossier
from app.services.case_manager import case_manager
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/report", tags=["Report"])

@router.get("/{case_id}", response_model=InvestigationDossier)
async def get_investigation_report(case_id: str):
    """Generates structured JSON investigation dossier with SHA-256 cryptographic provenance."""
    dossier = case_manager.get_investigation_dossier(case_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Cannot generate report for case '{case_id}'.")
    return dossier

@router.get("/{case_id}/markdown", response_class=PlainTextResponse)
async def get_markdown_report(case_id: str):
    """Generates formatted Markdown brief."""
    dossier = case_manager.get_investigation_dossier(case_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Cannot generate report for case '{case_id}'.")
    return ReportGenerator.format_markdown_report(dossier)
