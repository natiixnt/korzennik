"""GEDCOM import/export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Person, PersonEvent, PersonName, Relationship
from ..services.gedcom_service import export_gedcom, import_gedcom

router = APIRouter(prefix="/api/gedcom", tags=["gedcom"])


@router.post("/import")
async def import_gedcom_file(
    file: UploadFile, db: AsyncSession = Depends(get_db)
):
    """Import a GEDCOM file and create persons/relationships."""
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    count = await import_gedcom(db, text)
    return {"imported_persons": count}


@router.get("/export")
async def export_gedcom_file(db: AsyncSession = Depends(get_db)):
    """Export the tree as a GEDCOM 5.5.1 file."""
    gedcom_text = await export_gedcom(db)
    return PlainTextResponse(
        content=gedcom_text,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=korzennik_export.ged"},
    )
