from fastapi import APIRouter, HTTPException, status

from app.schemas.analysis import Finding
from app.schemas.summary import PRSummaryResponse
from app.services.agents.pr_summary_agent import pr_summary_agent
from app.services.storage_service import storage_service

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/{analysis_id}", response_model=PRSummaryResponse)
@router.post("/{analysis_id}", response_model=PRSummaryResponse)
def get_pr_summary(analysis_id: str):
    """
    Generates or retrieves a structured Pull Request style review summary
    for the specified code analysis submission.
    """
    analysis_data = storage_service.get_analysis(analysis_id)
    if not analysis_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis submission with ID '{analysis_id}' not found",
        )

    findings_raw = analysis_data.get("findings") or []
    findings = [Finding.model_validate(f) for f in findings_raw]

    summary = pr_summary_agent.generate_summary(
        analysis_id=analysis_id,
        findings=findings,
        code=analysis_data.get("code", ""),
        language=analysis_data.get("language", "python"),
    )

    return summary
