# import zipfile
# import shutil
# import uuid
# from pathlib import Path
# from fastapi import UploadFile, HTTPException

# UPLOAD_DIR = Path("/tmp/pipeline_ui_sessions")
# UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# async def extract_zip(file: UploadFile) -> dict:
#     if not file.filename.endswith(".zip"):
#         raise HTTPException(status_code=400, detail="Only .zip files are supported")

#     session_id = str(uuid.uuid4())
#     session_dir = UPLOAD_DIR / session_id
#     session_dir.mkdir(parents=True, exist_ok=True)

#     zip_path = session_dir / "upload.zip"
#     extract_path = session_dir / "project"
#     extract_path.mkdir(parents=True, exist_ok=True)

#     content = await file.read()
#     with open(zip_path, "wb") as f:
#         f.write(content)

#     try:
#         with zipfile.ZipFile(zip_path, "r") as zf:
#             zf.extractall(extract_path)
#     except zipfile.BadZipFile:
#         shutil.rmtree(session_dir)
#         raise HTTPException(status_code=400, detail="Invalid ZIP file")

#     file_count = sum(1 for _ in extract_path.rglob("*") if _.is_file())
#     zip_path.unlink()

#     return {
#         "session_id": session_id,
#         "extracted_path": str(extract_path),
#         "file_count": file_count,
#     }
import zipfile
import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException

UPLOAD_DIR = Path("/tmp/pipeline_ui_sessions")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def extract_zip(file: UploadFile) -> dict:
    """Extract uploaded ZIP to a temp session directory."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    zip_path = session_dir / "upload.zip"
    extract_path = session_dir / "project"
    extract_path.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    with open(zip_path, "wb") as f:
        f.write(content)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_path)
    except zipfile.BadZipFile:
        shutil.rmtree(session_dir)
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    file_count = sum(1 for _ in extract_path.rglob("*") if _.is_file())
    zip_path.unlink()

    return {
        "session_id": session_id,
        "extracted_path": str(extract_path),
        "file_count": file_count,
    }


def get_session_path(session_id: str) -> Path:
    """Get the project path for a session."""
    path = UPLOAD_DIR / session_id / "project"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return path


def cleanup_session(session_id: str):
    """Remove session directory."""
    session_dir = UPLOAD_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)




def setup_test_workspace(session_id: str) -> dict:
    """Create test-specific directories in session workspace.
    
    Returns dict with paths to:
    - tests/ - for generated .spec.ts files
    - test-results/ - for Playwright JSON output
    - artifacts/ - for screenshots/videos/traces
    """
    session_dir = UPLOAD_DIR / session_id
    
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    tests_dir = session_dir / "tests"
    results_dir = session_dir / "test-results"
    artifacts_dir = session_dir / "artifacts"
    
    tests_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)
    artifacts_dir.mkdir(exist_ok=True)
    
    return {
        "tests_dir": str(tests_dir),
        "results_dir": str(results_dir),
        "artifacts_dir": str(artifacts_dir),
    }
