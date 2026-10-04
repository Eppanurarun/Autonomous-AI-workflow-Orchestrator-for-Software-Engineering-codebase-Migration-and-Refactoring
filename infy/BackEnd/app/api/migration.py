"""
Migration API Router
=====================
Handles all /api/migration/* endpoints for the Java → Julia migration module.

Endpoints:
    POST /api/migration/analyze        — Migration analysis of Java code
    POST /api/migration/convert        — Java → Julia conversion
    POST /api/migration/risk-analysis  — Risk categorization
    POST /api/migration/detect-errors  — Error detection in Julia output
    POST /api/migration/correct-errors — Iterative error correction
    POST /api/migration/validate       — Functional validation
    POST /api/migration/run            — Complete pipeline (all steps)

This router is completely independent from existing API routes.
"""

import os
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel

from app.services.agents.migration import (
    migration_analysis_agent,
    java_to_julia_agent,
    migration_risk_agent,
    migration_error_detection_agent,
    migration_error_correction_agent,
    migration_validation_agent,
)

router = APIRouter(prefix="/migration", tags=["migration"])


# ============================================================
# REQUEST / RESPONSE SCHEMAS
# ============================================================

class JavaCodeRequest(BaseModel):
    java_code: str
    filename: Optional[str] = None


class JuliaConvertRequest(BaseModel):
    java_code: str
    analysis: Optional[dict] = None


class RiskAnalysisRequest(BaseModel):
    java_code: str
    julia_code: str
    analysis: Optional[dict] = None


class ErrorDetectionRequest(BaseModel):
    julia_code: str
    java_code: Optional[str] = ""


class ErrorCorrectionRequest(BaseModel):
    java_code: str
    julia_code: str
    errors: list
    analysis: Optional[dict] = None
    risks: Optional[list] = None
    iteration: Optional[int] = 1


class ValidationRequest(BaseModel):
    java_code: str
    julia_code: str
    analysis: Optional[dict] = None
    errors_remaining: Optional[int] = 0


class MigrationRunRequest(BaseModel):
    java_code: str
    filename: Optional[str] = None


# ============================================================
# HELPER — validate Java source
# ============================================================

def _validate_java_code(code: str, filename: Optional[str] = None) -> None:
    """Validate that the input is Java source code."""

    if not code or not code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Java code provided. Please upload or paste Java source code.",
        )

    stripped = code.strip()

    # Basic Java indicators
    java_indicators = [
        "class ", "interface ", "public ", "private ", "protected ",
        "import ", "package ", "void ", "static ", "final ",
        "System.out", "public static void main",
    ]

    has_java_indicator = any(indicator in stripped for indicator in java_indicators)

    if not has_java_indicator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provided code does not appear to be valid Java source code. "
                   "Please upload a .java file or paste valid Java code.",
        )

    # Validate filename extension if provided
    if filename:
        _, ext = os.path.splitext(filename)
        if ext.lower() not in (".java",):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension '{ext}'. Only .java files are supported for migration.",
            )


# ============================================================
# INDIVIDUAL STEP ENDPOINTS
# ============================================================

@router.post("/analyze")
async def analyze_java_code(payload: JavaCodeRequest):
    """Step 1: Analyze Java code structure for migration."""

    _validate_java_code(payload.java_code, payload.filename)

    result = await asyncio.to_thread(
        migration_analysis_agent.analyze,
        payload.java_code,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result["error"],
        )

    return {"status": "success", "analysis": result}


@router.post("/convert")
async def convert_java_to_julia(payload: JuliaConvertRequest):
    """Step 2: Convert Java code to Julia."""

    _validate_java_code(payload.java_code)

    result = await asyncio.to_thread(
        java_to_julia_agent.convert,
        payload.java_code,
        payload.analysis,
    )

    if "error" in result and not result.get("julia_code"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result["error"],
        )

    return {"status": "success", "conversion": result}


@router.post("/risk-analysis")
async def analyze_migration_risks(payload: RiskAnalysisRequest):
    """Step 3: Analyze migration risks."""

    result = await asyncio.to_thread(
        migration_risk_agent.analyze_risks,
        payload.java_code,
        payload.julia_code,
        payload.analysis,
    )

    return {"status": "success", "risk_analysis": result}


@router.post("/detect-errors")
async def detect_migration_errors(payload: ErrorDetectionRequest):
    """Step 4: Detect errors in generated Julia code."""

    result = await asyncio.to_thread(
        migration_error_detection_agent.detect_errors,
        payload.julia_code,
        payload.java_code or "",
    )

    return {"status": "success", "error_detection": result}


@router.post("/correct-errors")
async def correct_migration_errors(payload: ErrorCorrectionRequest):
    """Step 5: Correct errors in Julia code."""

    result = await asyncio.to_thread(
        migration_error_correction_agent.correct_errors,
        payload.java_code,
        payload.julia_code,
        payload.errors,
        payload.analysis,
        payload.risks,
        payload.iteration or 1,
    )

    return {"status": "success", "correction": result}


@router.post("/validate")
async def validate_migration(payload: ValidationRequest):
    """Step 6: Validate functional equivalence."""

    result = await asyncio.to_thread(
        migration_validation_agent.validate,
        payload.java_code,
        payload.julia_code,
        payload.analysis,
        payload.errors_remaining or 0,
    )

    return {"status": "success", "validation": result}


# ============================================================
# COMPLETE PIPELINE ENDPOINT
# ============================================================

@router.post("/run")
async def run_complete_migration(payload: MigrationRunRequest):
    """
    Execute the complete Java → Julia migration pipeline.

    Steps:
        1. Migration Analysis
        2. Java → Julia Conversion
        3. Migration Risk Analysis
        4. Error Detection
        5. Error Correction (iterative, max 3 rounds)
        6. Functional Validation
    """

    _validate_java_code(payload.java_code, payload.filename)

    pipeline_result = {
        "filename": payload.filename or "Uploaded.java",
        "java_code": payload.java_code,
        "steps": {},
    }

    try:
        # ── Step 1: Migration Analysis ──────────────────────────
        analysis = await asyncio.to_thread(
            migration_analysis_agent.analyze,
            payload.java_code,
        )
        pipeline_result["steps"]["analysis"] = {
            "status": "completed",
            "result": analysis,
        }

        # ── Step 2: Java → Julia Conversion ─────────────────────
        conversion = await asyncio.to_thread(
            java_to_julia_agent.convert,
            payload.java_code,
            analysis,
        )

        if not conversion.get("julia_code"):
            pipeline_result["steps"]["conversion"] = {
                "status": "failed",
                "result": conversion,
            }
            pipeline_result["status"] = "failed"
            pipeline_result["error"] = conversion.get("error", "Conversion produced no Julia code")
            pipeline_result["julia_code"] = ""
            return pipeline_result

        pipeline_result["steps"]["conversion"] = {
            "status": "completed",
            "result": conversion,
        }
        current_julia_code = conversion["julia_code"]

        # ── Step 3: Migration Risk Analysis ─────────────────────
        risk_result = await asyncio.to_thread(
            migration_risk_agent.analyze_risks,
            payload.java_code,
            current_julia_code,
            analysis,
        )
        pipeline_result["steps"]["risk_analysis"] = {
            "status": "completed",
            "result": risk_result,
        }

        # ── Steps 4 & 5: Error Detection + Correction (iterative) ──
        max_retries = 3
        all_corrections = []
        final_error_result = None

        for iteration in range(1, max_retries + 1):
            # Detect errors
            error_result = await asyncio.to_thread(
                migration_error_detection_agent.detect_errors,
                current_julia_code,
                payload.java_code,
            )
            final_error_result = error_result

            # If no critical errors, stop
            if not error_result["summary"]["has_critical_errors"] and error_result["summary"]["total"] <= 2:
                break

            # Attempt correction
            correction_result = await asyncio.to_thread(
                migration_error_correction_agent.correct_errors,
                payload.java_code,
                current_julia_code,
                error_result["errors"],
                analysis,
                risk_result.get("risks", []),
                iteration,
            )

            if correction_result.get("status") == "corrected" and correction_result.get("corrected_julia_code"):
                current_julia_code = correction_result["corrected_julia_code"]
                all_corrections.append({
                    "iteration": iteration,
                    "corrections": correction_result.get("corrections_made", []),
                })
            else:
                break

        pipeline_result["steps"]["error_detection"] = {
            "status": "completed",
            "result": final_error_result,
        }
        pipeline_result["steps"]["error_correction"] = {
            "status": "completed",
            "iterations": len(all_corrections),
            "corrections": all_corrections,
        }

        # ── Step 6: Functional Validation ───────────────────────
        errors_remaining = final_error_result["summary"]["total"] if final_error_result else 0

        validation = await asyncio.to_thread(
            migration_validation_agent.validate,
            payload.java_code,
            current_julia_code,
            analysis,
            errors_remaining,
        )
        pipeline_result["steps"]["validation"] = {
            "status": "completed",
            "result": validation,
        }

        # ── Build final result ──────────────────────────────────
        pipeline_result["julia_code"] = current_julia_code
        pipeline_result["status"] = "completed"
        pipeline_result["summary"] = {
            "source_language": "Java",
            "target_language": "Julia",
            "migration_status": "Completed",
            "risk_level": risk_result.get("summary", {}).get("overall_risk_level", "UNKNOWN"),
            "errors_detected": final_error_result["summary"]["total"] if final_error_result else 0,
            "errors_corrected": sum(
                len(c.get("corrections", []))
                for c in all_corrections
            ),
            "correction_iterations": len(all_corrections),
            "validation_status": validation.get("status", "UNKNOWN"),
            "validation_confidence": validation.get("overall_confidence", 0),
        }

        return pipeline_result

    except Exception as e:
        pipeline_result["status"] = "error"
        pipeline_result["error"] = f"Migration pipeline failed: {str(e)}"
        pipeline_result["julia_code"] = pipeline_result.get("julia_code", "")
        return pipeline_result


# ============================================================
# FILE UPLOAD ENDPOINT
# ============================================================

@router.post("/upload")
async def upload_java_file(file: UploadFile = File(...)):
    """
    Upload a .java file and return its contents for migration.
    Does NOT run the migration pipeline — use /run after upload.
    """

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )

    _, ext = os.path.splitext(file.filename)
    if ext.lower() != ".java":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Only .java files are supported.",
        )

    try:
        content = await file.read()
        code = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read file. Ensure it is a valid UTF-8 text file.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading file: {str(e)}",
        )

    if not code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    # Size check (1MB max, matching existing config)
    if len(content) > 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds maximum size of 1MB.",
        )

    return {
        "status": "success",
        "filename": file.filename,
        "java_code": code,
        "lines": len(code.splitlines()),
        "size_bytes": len(content),
    }
