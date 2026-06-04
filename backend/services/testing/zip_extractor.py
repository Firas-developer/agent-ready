"""
ZIP Extractor for Testing - Uses existing pipeline_ui_sessions folder
"""
import zipfile
import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException

# Reuse existing UPLOAD_DIR
UPLOAD_DIR = Path("/tmp/pipeline_ui_sessions")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def extract_test_zip(file: UploadFile) -> dict:
    """Extract uploaded ZIP to testing workspace."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    session_id = str(uuid.uuid4())
    workspace_dir = UPLOAD_DIR / session_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    zip_path = workspace_dir / "upload.zip"
    project_dir = workspace_dir / "project"
    project_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    with open(zip_path, "wb") as f:
        f.write(content)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(project_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(workspace_dir)
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    file_count = sum(1 for _ in project_dir.rglob("*") if _.is_file())
    zip_path.unlink()

    # Create test directories
    tests_dir = workspace_dir / "tests"
    results_dir = workspace_dir / "results"
    screenshots_dir = workspace_dir / "screenshots"

    tests_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)
    screenshots_dir.mkdir(exist_ok=True)

    return {
        "session_id": session_id,
        "workspace_path": str(workspace_dir),
        "project_path": str(project_dir),
        "file_count": file_count,
        "tests_dir": str(tests_dir),
        "results_dir": str(results_dir),
        "screenshots_dir": str(screenshots_dir)
    }


def cleanup_test_session(session_id: str):
    """Remove session workspace."""
    workspace_dir = UPLOAD_DIR / session_id
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
