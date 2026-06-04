"""
Testing Router - Fixed JSON parsing
"""
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from services.testing import zip_extractor, session, feature_analyzer, reporter
from services.testing import zip_extractor, session, feature_analyzer, test_executor, reporter
# from services.testing import test_executor_playwright as test_executor
import json

router = APIRouter(prefix="/api/testing", tags=["Testing"])


@router.post("/unified-workflow")
async def unified_workflow(
    file: UploadFile = File(...),
    app_url: str = Form(...),
    username: str = Form(None),
    password: str = Form(None),
    provider: str = Form("azure_foundry_claude"),
    model: str = Form(None),
):
    """
    🚀 UNIFIED WORKFLOW - Complete end-to-end testing
    """
    # Extract ZIP
    result = await zip_extractor.extract_test_zip(file)
    session_id = result["session_id"]
    project_path = result["project_path"]
    workspace_path = result["workspace_path"] 
    
    # Create session
    session.create_test_session(session_id, result["workspace_path"], project_path, app_url)
    
    # Build credentials
    credentials = None
    if username and password:
        credentials = {"username": username, "password": password}
    
    async def event_stream():
        yield f"data: 🚀 UNIFIED TESTING WORKFLOW\n\n"
        yield f"data: 📁 Session: {session_id}\n\n"
        yield f"data: 🌐 Target: {app_url}\n\n"
        yield f"data: ✅ Extracted {result['file_count']} files\n\n"
        yield "data: \n\n"
        
        # ============================================
        # PHASE 1: FEATURE DETECTION
        # ============================================
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        yield "data: 📊 PHASE 1: Feature Detection\n\n"
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        features = []
        json_buffer = ""
        collecting_json = False
        
        # Call feature analyzer
        async for chunk in feature_analyzer.analyze_and_detect_features(
            project_path, provider, model
        ):
            if "__FEATURES_JSON__" in chunk:
                collecting_json = True
                yield chunk  # Send the marker
                continue
            
            if collecting_json:
                # Collect JSON lines
                json_line = chunk.replace("data: ", "").strip()
                if json_line:
                    json_buffer += json_line
            else:
                yield chunk
        
        # Parse collected JSON
        if json_buffer:
            try:
                features = json.loads(json_buffer)
                if not isinstance(features, list):
                    features = []
            except Exception as e:
                yield f"data: ⚠️ JSON parse error: {e}\n\n"
                features = []
        
        # Store features
        session.set_features(session_id, features)
        
        yield f"data: ✅ Detection complete: {len(features)} features stored\n\n"
        yield "data: \n\n"
        
        # ============================================
        # PHASE 2: TEST EXECUTION
        # ============================================
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        yield "data: 🧪 PHASE 2: Test Execution\n\n"
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if not features:
            yield "data: ⚠️ No features to test\n\n"
        else:
            # Execute tests
            async for chunk in test_executor.execute_all_tests(
                session_id, project_path, app_url, features, credentials, workspace_path
            ):
                if "__RESULTS_JSON__" not in chunk:
                    yield chunk
        
        # ============================================
        # PHASE 3: REPORTING
        # ============================================
        yield "data: \n\n"
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        yield "data: 📊 FINAL REPORT\n\n"
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Generate report
        report = reporter.generate_test_report(session_id)
        
        yield f"data: 📊 Total Features: {report['total_features']}\n\n"
        yield f"data: ✅ Passed: {report['passed']}\n\n"
        yield f"data: ❌ Failed: {report['failed']}\n\n"
        yield f"data: ⏩ Skipped: {report['skipped']}\n\n"
        
        if report['executed'] > 0:
            yield f"data: 📈 Pass Rate: {report['pass_rate']:.1f}%\n\n"
        
        yield "data: \n\n"
        yield "data: __REPORT_JSON__\n\n"
        yield f"data: {json.dumps(report, indent=2)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Session-ID": session_id,
        },
    )


@router.get("/report/{session_id}")
async def get_report(session_id: str):
    """Get test report for a session."""
    return reporter.generate_test_report(session_id)


@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    """Get complete session data."""
    return session.get_test_session(session_id)


@router.get("/features/{session_id}")
async def get_features(session_id: str):
    """Get detected features for a session."""
    sess = session.get_test_session(session_id)
    return {
        "session_id": session_id,
        "features": sess.get("features", []),
        "count": len(sess.get("features", []))
    }


@router.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up session data and files."""
    session.cleanup_test_session(session_id)
    zip_extractor.cleanup_test_session(session_id)
    return {"status": "cleaned", "session_id": session_id}
