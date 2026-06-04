from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from services.zip_handler import extract_zip
from services.agent_ready_service import stream_agent_ready

router = APIRouter(prefix="/api/agent-ready", tags=["Agent Ready"])


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    provider: str = Form("azure_foundry_claude"),
    model: str = Form(None),
):
    result = await extract_zip(file)
    session_id = result["session_id"]
    project_path = result["extracted_path"]
    file_count = result["file_count"]

    async def event_stream():
        yield f"data: ✓ Session: {session_id}\n\n"
        yield f"data: ✓ Extracted {file_count} files\n\n"
        async for chunk in stream_agent_ready(project_path, provider, model):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-ID": session_id,
        },
    )
