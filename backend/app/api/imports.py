from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_session
from app.importing.stocks26 import preview_movimenti

router = APIRouter(prefix="/api/imports", tags=["imports"], dependencies=[Depends(require_session)])


class CsvPreviewRequest(BaseModel):
    csv: str


@router.post("/stocks26/preview")
def preview(payload: CsvPreviewRequest) -> dict:
    if len(payload.csv.encode("utf-8")) > 5_000_000:
        raise HTTPException(status_code=413, detail="CSV export is too large")
    with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".csv", delete=False) as temporary:
        temporary.write(payload.csv)
        path = Path(temporary.name)
    try:
        result = preview_movimenti(path)
    finally:
        path.unlink(missing_ok=True)
    return {"source_hash": result.source_hash, "valid_rows": result.valid_rows, "errors": result.errors}
