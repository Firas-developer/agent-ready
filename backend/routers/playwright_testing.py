# """
# Playwright Testing router — API endpoints for test generation and execution.
# Follows same SSE streaming pattern as agent_ready.py.
# """
# from fastapi import APIRouter, UploadFile, File, Form, HTTPException
# from fastapi.responses import StreamingResponse, FileResponse, Response
# from pathlib import Path
# import json
# from services.zip_handler import extract_zip
# from services.playwright_testing import session_manager

# router = APIRouter(prefix="/api/playwright-testing", tags=["Playwright Testing"])


# @router.post("/analyze")
# async def analyze(
#     file: UploadFile = File(...),
#     provider: str = Form("azure_foundry_claude"),
#     model: str = Form(None),
#     app_url: str = Form(None),
# ):
#     """
#     Step 1: Upload project ZIP and detect testable features.
#     Returns: SSE stream with progress + features stored in session.
#     """
#     # Extract ZIP (reuse existing zip_handler)
#     result = await extract_zip(file)
#     session_id = result["session_id"]
#     project_path = result["extracted_path"]
#     file_count = result["file_count"]
    
#     # Create test session
#     session_manager.create_session(session_id, project_path, app_url)
    
#     async def event_stream():
#         yield f"data: ✓ Session: {session_id}\n\n"
#         yield f"data: ✓ Extracted {file_count} files\n\n"
#         yield f"data: 🔍 Analyzing codebase for testable features...\n\n"
        
#         # Import feature detector
#         from services.playwright_testing import feature_detector
        
#         # Call real feature detector
#         features_json_str = ""
#         capture_json = False
        
#         async for chunk in feature_detector.detect_features(project_path, provider, model):
#             # Check for JSON markers
#             if "__FEATURES_JSON_START__" in chunk:
#                 capture_json = True
#                 continue
#             elif "__FEATURES_JSON_END__" in chunk:
#                 capture_json = False
#                 continue
            
#             if capture_json:
#                 # Extract JSON content
#                 json_content = chunk.replace("data: ", "").strip()
#                 features_json_str += json_content
#             else:
#                 # Stream progress to user
#                 yield chunk
        
#         # Parse features
#         try:
#             detected_features = json.loads(features_json_str) if features_json_str else []
#         except json.JSONDecodeError as e:
#             yield f"data: ⚠️ Error parsing features JSON: {e}\n\n"
#             detected_features = []
        
#         # Store features in session
#         if detected_features:
#             session_manager.add_features(session_id, detected_features)
#             yield f"data: ✅ Stored {len(detected_features)} features in session\n\n"
#         else:
#             # Fallback feature if detection failed
#             fallback = [{
#                 "id": "feat-fallback",
#                 "name": "Manual Testing Required",
#                 "type": "manual",
#                 "priority": "medium",
#                 "entry_point": "/",
#                 "description": "Feature detection failed. Add features manually or retry.",
#                 "detected_from": [],
#                 "selectors": {},
#                 "test_scenario": ["Navigate to /", "Verify page loads"],
#                 "test_generated": False,
#                 "test_status": "not_run"
#             }]
#             session_manager.add_features(session_id, fallback)
#             yield f"data: ⚠️ Created fallback feature\n\n"
        
#         yield "data: [DONE]\n\n"
    
#     return StreamingResponse(
#         event_stream(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "X-Accel-Buffering": "no",
#             "X-Session-ID": session_id,
#         },
#     )


# @router.post("/generate-test/{session_id}")
# async def generate_test(
#     session_id: str,
#     feature_id: str = Form(...),
#     provider: str = Form("azure_foundry_claude"),
#     model: str = Form(None),
# ):
#     """
#     Step 2: Generate Playwright test for a specific feature.
#     Returns: SSE stream with test generation progress + saves test file.
#     """
#     # Verify session exists
#     session = session_manager.get_session(session_id)
#     feature = session_manager.get_feature(session_id, feature_id)
#     project_path = session["project_path"]
    
#     async def event_stream():
#         # Import test generator
#         from services.playwright_testing import test_generator
        
#         # Call real test generator
#         test_code_str = ""
#         capture_code = False
        
#         async for chunk in test_generator.generate_test(feature, project_path, provider, model):
#             # Check for test code markers
#             if "__TEST_CODE_START__" in chunk:
#                 capture_code = True
#                 continue
#             elif "__TEST_CODE_END__" in chunk:
#                 capture_code = False
#                 continue
            
#             if capture_code:
#                 # Extract test code content
#                 code_content = chunk.replace("data: ", "").strip()
#                 test_code_str += code_content + "\n"
#             else:
#                 # Stream progress to user
#                 yield chunk
        
#         # Save test file to session directory
#         if test_code_str.strip():
#             try:
#                 tests_dir = Path(session["tests_dir"])
#                 test_file_path = tests_dir / f"{feature_id}.spec.ts"
                
#                 test_file_path.write_text(test_code_str, encoding='utf-8')
                
#                 yield f"data: 💾 Saved test file: {test_file_path.name}\n\n"
                
#                 # Update feature in session
#                 session_manager.update_feature(session_id, feature_id, {
#                     "test_generated": True,
#                     "test_file": f"tests/{feature_id}.spec.ts",
#                     "test_code": test_code_str[:500] + "..." if len(test_code_str) > 500 else test_code_str
#                 })
                
#                 yield f"data: ✅ Test generation complete!\n\n"
                
#             except Exception as e:
#                 yield f"data: ✗ Error saving test file: {e}\n\n"
#         else:
#             yield f"data: ⚠️ No test code generated\n\n"
        
#         yield "data: [DONE]\n\n"
    
#     return StreamingResponse(
#         event_stream(),
#         media_type="text/event-stream",
#         headers={"Cache-Control": "no-cache"},
#     )

# @router.get("/test-code/{session_id}/{feature_id}")
# async def get_test_code(session_id: str, feature_id: str):
#     """
#     Get the generated test code for a feature.
#     Returns: Test file content as plain text.
#     """
#     session = session_manager.get_session(session_id)
#     feature = session_manager.get_feature(session_id, feature_id)
    
#     # Check if test was generated
#     if not feature.get("test_generated"):
#         raise HTTPException(status_code=404, detail="Test not yet generated for this feature")
    
#     # Read test file
#     test_file = feature.get("test_file")
#     if not test_file:
#         raise HTTPException(status_code=404, detail="Test file path not found")
    
#     tests_dir = Path(session["tests_dir"])
#     test_file_path = tests_dir / Path(test_file).name
    
#     if not test_file_path.exists():
#         raise HTTPException(status_code=404, detail="Test file not found on disk")
    
#     try:
#         test_code = test_file_path.read_text(encoding='utf-8')
#         return Response(content=test_code, media_type="text/plain; charset=utf-8")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error reading test file: {e}")


# @router.post("/run-test/{session_id}")
# async def run_test(
#     session_id: str,
#     feature_id: str = Form(...),
#     app_url: str = Form(...),
# ):
#     """
#     Step 3: Execute Playwright test against provided URL.
#     Returns: SSE stream with test execution progress.
#     """
#     # Verify session and feature
#     session = session_manager.get_session(session_id)
#     feature = session_manager.get_feature(session_id, feature_id)
    
#     # Update app_url if provided
#     session_manager.set_app_url(session_id, app_url)
    
#     async def event_stream():
#         yield f"data: 🎭 Running test: {feature['name']}\n\n"
#         yield f"data: 🌐 Target URL: {app_url}\n\n"
        
#         # TODO Phase 4: Call test_executor.run_test()
#         yield f"data: ⚠️ Test execution not yet implemented\n\n"
#         yield f"data: 📋 This will run: npx playwright test {feature.get('test_file', 'test.spec.ts')}\n\n"
        
#         # Placeholder - mark as passed
#         session_manager.update_feature(session_id, feature_id, {
#             "test_status": "passed",
#             "last_run": "2026-04-26T12:48:00Z",
#             "test_duration_ms": 2341
#         })
        
#         yield f"data: ✅ Test completed: PASSED (2.3s)\n\n"
#         yield f"data: [DONE]\n\n"
    
#     return StreamingResponse(
#         event_stream(),
#         media_type="text/event-stream",
#         headers={"Cache-Control": "no-cache"},
#     )


# @router.get("/results/{session_id}/{feature_id}")
# async def get_results(session_id: str, feature_id: str):
#     """
#     Step 4: Get test results for a specific feature.
#     Returns: JSON with test report.
#     """
#     session = session_manager.get_session(session_id)
#     feature = session_manager.get_feature(session_id, feature_id)
    
#     # TODO Phase 5: Call test_reporter.parse_test_results()
#     # For now, return feature data
#     return {
#         "session_id": session_id,
#         "feature": feature,
#         "status": feature.get("test_status", "not_run"),
#         "duration_ms": feature.get("test_duration_ms", 0),
#         "artifacts": feature.get("artifacts", {}),
#     }


# @router.get("/session/{session_id}")
# async def get_session(session_id: str):
#     """Get full session data including all features."""
#     session = session_manager.get_session(session_id)
#     return session


# @router.get("/features/{session_id}")
# async def get_features(session_id: str):
#     """Get just the features list for a session (useful for frontend)."""
#     session = session_manager.get_session(session_id)
#     return {
#         "session_id": session_id,
#         "app_url": session.get("app_url"),
#         "features": session.get("features", []),
#         "feature_count": len(session.get("features", []))
#     }


# @router.get("/artifact/{session_id}/{artifact_path:path}")
# async def get_artifact(session_id: str, artifact_path: str):
#     """
#     Serve test artifacts (screenshots, videos, traces).
#     Similar to visualizer's /source endpoint.
#     """
#     session = session_manager.get_session(session_id)
#     artifacts_dir = Path(session["artifacts_dir"])
    
#     # Security check - ensure path is within artifacts directory
#     file_path = (artifacts_dir / artifact_path).resolve()
#     try:
#         file_path.relative_to(artifacts_dir.resolve())
#     except ValueError:
#         raise HTTPException(status_code=403, detail="Access denied")
    
#     if not file_path.is_file():
#         raise HTTPException(status_code=404, detail="Artifact not found")
    
#     # Determine media type
#     suffix = file_path.suffix.lower()
#     media_types = {
#         ".png": "image/png",
#         ".jpg": "image/jpeg",
#         ".jpeg": "image/jpeg",
#         ".webm": "video/webm",
#         ".mp4": "video/mp4",
#         ".zip": "application/zip",
#         ".json": "application/json",
#         ".html": "text/html",
#     }
#     media_type = media_types.get(suffix, "application/octet-stream")
    
#     return FileResponse(file_path, media_type=media_type)


# @router.delete("/session/{session_id}")
# async def cleanup(session_id: str):
#     """Clean up session (remove from memory and disk)."""
#     from services.zip_handler import cleanup_session as cleanup_zip_session
    
#     # Clean up session manager
#     session_manager.cleanup_session(session_id)
    
#     # Clean up files
#     cleanup_zip_session(session_id)
    
#     return {"status": "cleaned", "session_id": session_id}


# @router.post("/update-app-url/{session_id}")
# async def update_app_url(
#     session_id: str,
#     app_url: str = Form(...),
# ):
#     """Update the application URL for a session."""
#     session_manager.set_app_url(session_id, app_url)
#     return {
#         "session_id": session_id,
#         "app_url": app_url,
#         "status": "updated"
#     }
"""
Playwright Testing router — API endpoints for test generation and execution.
Follows same SSE streaming pattern as agent_ready.py.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, Response
from pathlib import Path
import json
import time
from datetime import datetime
from services.zip_handler import extract_zip
from services.playwright_testing import session_manager

router = APIRouter(prefix="/api/playwright-testing", tags=["Playwright Testing"])


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    provider: str = Form("azure_foundry_claude"),
    model: str = Form(None),
    app_url: str = Form(None),
):
    """
    Step 1: Upload project ZIP and detect testable features.
    Returns: SSE stream with progress + features stored in session.
    """
    # Extract ZIP (reuse existing zip_handler)
    result = await extract_zip(file)
    session_id = result["session_id"]
    project_path = result["extracted_path"]
    file_count = result["file_count"]
    
    # Create test session
    session_manager.create_session(session_id, project_path, app_url)
    
    async def event_stream():
        yield f"data: ✓ Session: {session_id}\n\n"
        yield f"data: ✓ Extracted {file_count} files\n\n"
        yield f"data: 🔍 Analyzing codebase for testable features...\n\n"
        
        # Import feature detector
        from services.playwright_testing import feature_detector
        
        # Call real feature detector
        features_json_str = ""
        capture_json = False
        
        async for chunk in feature_detector.detect_features(project_path, provider, model):
            # Check for JSON markers
            if "__FEATURES_JSON_START__" in chunk:
                capture_json = True
                continue
            elif "__FEATURES_JSON_END__" in chunk:
                capture_json = False
                continue
            
            if capture_json:
                # Extract JSON content
                json_content = chunk.replace("data: ", "").strip()
                features_json_str += json_content
            else:
                # Stream progress to user
                yield chunk
        
        # Parse features
        try:
            detected_features = json.loads(features_json_str) if features_json_str else []
        except json.JSONDecodeError as e:
            yield f"data: ⚠️ Error parsing features JSON: {e}\n\n"
            detected_features = []
        
        # Store features in session
        if detected_features:
            session_manager.add_features(session_id, detected_features)
            yield f"data: ✅ Stored {len(detected_features)} features in session\n\n"
        else:
            # Fallback feature if detection failed
            fallback = [{
                "id": "feat-fallback",
                "name": "Manual Testing Required",
                "type": "manual",
                "priority": "medium",
                "entry_point": "/",
                "description": "Feature detection failed. Add features manually or retry.",
                "detected_from": [],
                "ui_components": {},
                "test_steps": [],
                "test_generated": False,
                "test_status": "not_run"
            }]
            session_manager.add_features(session_id, fallback)
            yield f"data: ⚠️ Created fallback feature\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-ID": session_id,
        },
    )


@router.post("/generate-test/{session_id}")
async def generate_test(
    session_id: str,
    feature_id: str = Form(...),
    provider: str = Form("azure_foundry_claude"),
    model: str = Form(None),
):
    """
    Step 2: Generate Playwright test for a specific feature.
    Returns: SSE stream with test generation progress + saves test file.
    """
    # Verify session exists
    session = session_manager.get_session(session_id)
    feature = session_manager.get_feature(session_id, feature_id)
    project_path = session["project_path"]
    
    async def event_stream():
        # Import test generator
        from services.playwright_testing import test_generator
        
        # Call real test generator
        test_code_str = ""
        capture_code = False
        
        async for chunk in test_generator.generate_test(feature, project_path, provider, model):
            # Check for test code markers
            if "__TEST_CODE_START__" in chunk:
                capture_code = True
                continue
            elif "__TEST_CODE_END__" in chunk:
                capture_code = False
                continue
            
            if capture_code:
                # Extract test code content
                code_content = chunk.replace("data: ", "").strip()
                test_code_str += code_content + "\n"
            else:
                # Stream progress to user
                yield chunk
        
        # Save test file to session directory
        if test_code_str.strip():
            try:
                tests_dir = Path(session["tests_dir"])
                test_file_path = tests_dir / f"{feature_id}.spec.ts"
                
                test_file_path.write_text(test_code_str, encoding='utf-8')
                
                yield f"data: 💾 Saved test file: {test_file_path.name}\n\n"
                
                # Update feature in session
                session_manager.update_feature(session_id, feature_id, {
                    "test_generated": True,
                    "test_file": f"tests/{feature_id}.spec.ts",
                    "test_code": test_code_str[:500] + "..." if len(test_code_str) > 500 else test_code_str
                })
                
                yield f"data: ✅ Test generation complete!\n\n"
                
            except Exception as e:
                yield f"data: ✗ Error saving test file: {e}\n\n"
        else:
            yield f"data: ⚠️ No test code generated\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/generate-all-tests/{session_id}")
async def generate_all_tests(
    session_id: str,
    provider: str = Form("azure_foundry_claude"),
    model: str = Form(None),
):
    """
    Generate Playwright tests for ALL features in the session.
    Returns: SSE stream with progress for each test generation.
    """
    # Verify session exists
    session = session_manager.get_session(session_id)
    features = session.get("features", [])
    
    if not features:
        raise HTTPException(status_code=404, detail="No features found in session")
    
    project_path = session["project_path"]
    
    async def event_stream():
        yield f"data: 🎯 Generating tests for ALL features ({len(features)} total)\n\n"
        yield "data: \n\n"
        
        # Track statistics
        total_features = len(features)
        generated_count = 0
        skipped_count = 0
        failed_count = 0
        
        # Generate tests for each feature
        for index, feature in enumerate(features, 1):
            feature_id = feature.get("id")
            feature_name = feature.get("name")
            
            yield f"data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            yield f"data: 📝 Feature {index}/{total_features}: {feature_name}\n\n"
            yield f"data: 🆔 Feature ID: {feature_id}\n\n"
            
            # Check if test already generated
            if feature.get("test_generated"):
                yield f"data: ⏩ Skipping - test already generated\n\n"
                skipped_count += 1
                continue
            
            # Import test generator
            from services.playwright_testing import test_generator
            
            # Generate test
            test_code_str = ""
            capture_code = False
            
            try:
                async for chunk in test_generator.generate_test(feature, project_path, provider, model):
                    # Check for test code markers
                    if "__TEST_CODE_START__" in chunk:
                        capture_code = True
                        continue
                    elif "__TEST_CODE_END__" in chunk:
                        capture_code = False
                        continue
                    
                    if capture_code:
                        # Capture test code
                        code_content = chunk.replace("data: ", "").strip()
                        test_code_str += code_content + "\n"
                    else:
                        # Stream progress
                        yield chunk
                
                # Save test file
                if test_code_str.strip():
                    tests_dir = Path(session["tests_dir"])
                    test_file_path = tests_dir / f"{feature_id}.spec.ts"
                    test_file_path.write_text(test_code_str, encoding='utf-8')
                    
                    # Update feature
                    session_manager.update_feature(session_id, feature_id, {
                        "test_generated": True,
                        "test_file": f"tests/{feature_id}.spec.ts",
                        "test_code": test_code_str[:500] + "..." if len(test_code_str) > 500 else test_code_str
                    })
                    
                    generated_count += 1
                    yield f"data: ✅ Test generated successfully\n\n"
                else:
                    failed_count += 1
                    yield f"data: ⚠️ No test code generated\n\n"
                    
            except Exception as e:
                failed_count += 1
                yield f"data: ❌ Error generating test: {e}\n\n"
            
            yield "data: \n\n"
        
        # Final summary
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        yield "data: 📊 GENERATION SUMMARY\n\n"
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        yield f"data: 📝 Total Features: {total_features}\n\n"
        yield f"data: ✅ Generated: {generated_count}\n\n"
        yield f"data: ⏩ Skipped: {skipped_count}\n\n"
        yield f"data: ❌ Failed: {failed_count}\n\n"
        yield "data: \n\n"
        
        if generated_count == total_features:
            yield "data: 🎉 ALL TESTS GENERATED SUCCESSFULLY!\n\n"
        elif failed_count == 0:
            yield "data: ✅ Test generation complete (some were already generated)\n\n"
        else:
            yield "data: ⚠️ Some tests failed to generate - check logs\n\n"
        
        yield "data: 💡 Next: Use /run-all-tests to execute all generated tests\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/test-code/{session_id}/{feature_id}")
async def get_test_code(session_id: str, feature_id: str):
    """
    Get the generated test code for a feature.
    Returns: Test file content as plain text.
    """
    session = session_manager.get_session(session_id)
    feature = session_manager.get_feature(session_id, feature_id)
    
    # Check if test was generated
    if not feature.get("test_generated"):
        raise HTTPException(status_code=404, detail="Test not yet generated for this feature")
    
    # Read test file
    test_file = feature.get("test_file")
    if not test_file:
        raise HTTPException(status_code=404, detail="Test file path not found")
    
    tests_dir = Path(session["tests_dir"])
    test_file_path = tests_dir / Path(test_file).name
    
    if not test_file_path.exists():
        raise HTTPException(status_code=404, detail="Test file not found on disk")
    
    try:
        test_code = test_file_path.read_text(encoding='utf-8')
        return Response(content=test_code, media_type="text/plain; charset=utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading test file: {e}")


@router.post("/run-test/{session_id}")
async def execute_test(
    session_id: str,
    feature_id: str = Form(...),
    app_url: str = Form(...),
    username: str = Form(None),
    password: str = Form(None),
):
    """
    Step 3: Execute Playwright test against provided URL.
    Optional: Provide username/password for authentication tests.
    Returns: SSE stream with test execution progress and results.
    """
    # Verify session and feature
    session = session_manager.get_session(session_id)
    feature = session_manager.get_feature(session_id, feature_id)
    
    # Update app_url if provided
    session_manager.set_app_url(session_id, app_url)
    
    # Build credentials dict if provided
    credentials = None
    if username and password:
        credentials = {
            "username": username,
            "email": username,
            "password": password
        }
    
    async def event_stream():
        # Import test executor
        from services.playwright_testing import test_executor
        
        # Call real test executor with credentials
        test_result_data = {}
        capture_result = False
        result_json_str = ""
        
        try:
            # 🔴 CRITICAL FIX: Pass feature dict instead of session_id, feature_id
            async for chunk in test_executor.execute_test(
                feature,                    # ✅ Pass full feature dict
                session["project_path"],   # ✅ Pass project path
                app_url,                   # ✅ Pass target URL
                credentials,               # ✅ Pass credentials
                "chromium"                 # ✅ Pass browser type
            ):
                # Check for result markers
                if "__TEST_RESULT_START__" in chunk:
                    capture_result = True
                    continue
                elif "__TEST_RESULT_END__" in chunk:
                    capture_result = False
                    continue
                
                if capture_result:
                    result_content = chunk.replace("data: ", "").strip()
                    result_json_str += result_content
                else:
                    yield chunk
        except Exception as e:
            yield f"data: ❌ Error during test execution: {e}\n\n"
        
        # Parse test results
        if result_json_str:
            try:
                test_result_data = json.loads(result_json_str)
            except json.JSONDecodeError:
                test_result_data = {"status": "error", "error": "Failed to parse results"}
        
        # Mark playwright as installed
        if not session.get("playwright_installed"):
            session_manager.mark_playwright_installed(session_id)
        
        # Update feature
        feature_updates = {
            "test_status": test_result_data.get("status", "unknown"),
            "last_run": datetime.utcnow().isoformat() + "Z",
            "test_duration_ms": test_result_data.get("duration_ms", 0),
            "test_result": test_result_data
        }
        
        session_manager.update_feature(session_id, feature_id, feature_updates)
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/run-all-tests/{session_id}")
async def run_all_tests(
    session_id: str,
    app_url: str = Form(...),
    username: str = Form(None),
    password: str = Form(None),
    skip_failed: bool = Form(False),
):
    """
    Run Playwright tests for ALL features in the session.
    Returns: SSE stream with progress for each test + final summary.
    """
    # Verify session exists
    session = session_manager.get_session(session_id)
    features = session.get("features", [])
    
    if not features:
        raise HTTPException(status_code=404, detail="No features found in session")
    
    # Update app_url
    session_manager.set_app_url(session_id, app_url)
    
    # Build credentials dict if provided
    credentials = None
    if username and password:
        credentials = {
            "username": username,
            "email": username,
            "password": password
        }
    
    async def event_stream():
        yield f"data: 🎯 Running tests for ALL features ({len(features)} total)\n\n"
        yield f"data: 🌐 Target URL: {app_url}\n\n"
        
        if credentials:
            yield f"data: 🔐 Using credentials: {username}\n\n"
        
        yield "data: \n\n"
        
        # Track results
        total_tests = len(features)
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        start_time = time.time()
        
        # Run tests for each feature
        for index, feature in enumerate(features, 1):
            feature_id = feature.get("id")
            feature_name = feature.get("name")
            
            yield f"data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            yield f"data: 📝 Test {index}/{total_tests}: {feature_name}\n\n"
            yield f"data: 🆔 Feature ID: {feature_id}\n\n"
            
            # Check if test was generated
            if not feature.get("test_generated"):
                yield f"data: ⚠️ Skipping - no test generated yet\n\n"
                skipped_tests += 1
                continue
            
            # Check if should skip failed tests
            if skip_failed and feature.get("test_status") == "failed":
                yield f"data: ⏩ Skipping - already failed\n\n"
                skipped_tests += 1
                continue
            
            # Run the test
            from services.playwright_testing import test_executor
            
            test_result_data = {}
            capture_result = False
            result_json_str = ""
            
            try:
                # 🔴 CRITICAL FIX: Pass feature dict instead of session_id, feature_id
                async for chunk in test_executor.execute_test(
                    feature,                    # ✅ Pass full feature dict
                    session["project_path"],   # ✅ Pass project path
                    app_url,                   # ✅ Pass target URL
                    credentials,               # ✅ Pass credentials
                    "chromium"                 # ✅ Pass browser type
                ):
                    # Check for result markers
                    if "__TEST_RESULT_START__" in chunk:
                        capture_result = True
                        continue
                    elif "__TEST_RESULT_END__" in chunk:
                        capture_result = False
                        continue
                    
                    if capture_result:
                        result_content = chunk.replace("data: ", "").strip()
                        result_json_str += result_content
                    else:
                        yield chunk
            except Exception as e:
                yield f"data: ❌ Error running test: {e}\n\n"
                failed_tests += 1
                continue
            
            # Parse result
            if result_json_str:
                try:
                    test_result_data = json.loads(result_json_str)
                    
                    # Update counts
                    if test_result_data.get("status") == "passed":
                        passed_tests += 1
                    else:
                        failed_tests += 1
                    
                    # Update feature
                    feature_updates = {
                        "test_status": test_result_data.get("status", "unknown"),
                        "last_run": datetime.utcnow().isoformat() + "Z",
                        "test_duration_ms": test_result_data.get("duration_ms", 0),
                        "test_result": test_result_data
                    }
                    session_manager.update_feature(session_id, feature_id, feature_updates)
                    
                except json.JSONDecodeError:
                    failed_tests += 1
            else:
                failed_tests += 1
            
            yield "data: \n\n"
        
        # Mark playwright as installed
        if not session.get("playwright_installed"):
            session_manager.mark_playwright_installed(session_id)
        
        # Calculate total duration
        total_duration = int((time.time() - start_time) * 1000)
        
        # Final summary
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        yield "data: 📊 FINAL SUMMARY\n\n"
        yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        yield f"data: 🧪 Total Tests: {total_tests}\n\n"
        yield f"data: ✅ Passed: {passed_tests}\n\n"
        yield f"data: ❌ Failed: {failed_tests}\n\n"
        yield f"data: ⏩ Skipped: {skipped_tests}\n\n"
        yield f"data: ⏱️ Total Duration: {total_duration}ms ({total_duration / 1000:.2f}s)\n\n"
        
        # Pass rate
        executed = passed_tests + failed_tests
        if executed > 0:
            pass_rate = (passed_tests / executed) * 100
            yield f"data: 📈 Pass Rate: {pass_rate:.1f}%\n\n"
        
        yield "data: \n\n"
        
        if passed_tests == total_tests - skipped_tests:
            yield "data: 🎉 ALL TESTS PASSED!\n\n"
        elif failed_tests > 0:
            yield "data: ⚠️ Some tests failed - check individual results\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/results/{session_id}/{feature_id}")
async def get_results(session_id: str, feature_id: str):
    """
    Step 4: Get test results for a specific feature.
    Returns: JSON with test report.
    """
    session = session_manager.get_session(session_id)
    feature = session_manager.get_feature(session_id, feature_id)
    
    return {
        "session_id": session_id,
        "feature_id": feature_id,
        "feature_name": feature.get("name"),
        "status": feature.get("test_status", "not_run"),
        "last_run": feature.get("last_run"),
        "duration_ms": feature.get("test_duration_ms", 0),
        "test_generated": feature.get("test_generated", False),
        "test_result": feature.get("test_result", {}),
        "artifacts": feature.get("artifacts", {}),
    }


@router.get("/test-summary/{session_id}")
async def get_test_summary(session_id: str):
    """
    Get a summary of all test results for a session.
    Returns: JSON with pass/fail counts and feature details.
    """
    session = session_manager.get_session(session_id)
    features = session.get("features", [])
    
    # Calculate statistics
    total = len(features)
    passed = sum(1 for f in features if f.get("test_status") == "passed")
    failed = sum(1 for f in features if f.get("test_status") == "failed")
    not_run = sum(1 for f in features if f.get("test_status") == "not_run")
    tests_generated = sum(1 for f in features if f.get("test_generated"))
    
    # Calculate total duration
    total_duration = sum(f.get("test_duration_ms", 0) for f in features)
    
    # Group by status
    by_status = {
        "passed": [f for f in features if f.get("test_status") == "passed"],
        "failed": [f for f in features if f.get("test_status") == "failed"],
        "not_run": [f for f in features if f.get("test_status") == "not_run"],
    }
    
    return {
        "session_id": session_id,
        "app_url": session.get("app_url"),
        "statistics": {
            "total_features": total,
            "tests_generated": tests_generated,
            "passed": passed,
            "failed": failed,
            "not_run": not_run,
            "pass_rate": (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0,
            "total_duration_ms": total_duration,
            "total_duration_seconds": total_duration / 1000
        },
        "by_status": {
            "passed": [{"id": f["id"], "name": f["name"]} for f in by_status["passed"]],
            "failed": [{"id": f["id"], "name": f["name"]} for f in by_status["failed"]],
            "not_run": [{"id": f["id"], "name": f["name"]} for f in by_status["not_run"]],
        }
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get full session data including all features."""
    session = session_manager.get_session(session_id)
    return session


@router.get("/features/{session_id}")
async def get_features(session_id: str):
    """Get just the features list for a session (useful for frontend)."""
    session = session_manager.get_session(session_id)
    return {
        "session_id": session_id,
        "app_url": session.get("app_url"),
        "features": session.get("features", []),
        "feature_count": len(session.get("features", []))
    }


@router.get("/artifact/{session_id}/{artifact_path:path}")
async def get_artifact(session_id: str, artifact_path: str):
    """
    Serve test artifacts (screenshots, videos, traces).
    Similar to visualizer's /source endpoint.
    """
    session = session_manager.get_session(session_id)
    artifacts_dir = Path(session["artifacts_dir"])
    
    # Security check - ensure path is within artifacts directory
    file_path = (artifacts_dir / artifact_path).resolve()
    try:
        file_path.relative_to(artifacts_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Determine media type
    suffix = file_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webm": "video/webm",
        ".mp4": "video/mp4",
        ".zip": "application/zip",
        ".json": "application/json",
        ".html": "text/html",
    }
    media_type = media_types.get(suffix, "application/octet-stream")
    
    return FileResponse(file_path, media_type=media_type)


@router.delete("/session/{session_id}")
async def cleanup(session_id: str):
    """Clean up session (remove from memory and disk)."""
    from services.zip_handler import cleanup_session as cleanup_zip_session
    
    # Clean up session manager
    session_manager.cleanup_session(session_id)
    
    # Clean up files
    cleanup_zip_session(session_id)
    
    return {"status": "cleaned", "session_id": session_id}


@router.post("/update-app-url/{session_id}")
async def update_app_url(
    session_id: str,
    app_url: str = Form(...),
):
    """Update the application URL for a session."""
    session_manager.set_app_url(session_id, app_url)
    return {
        "session_id": session_id,
        "app_url": app_url,
        "status": "updated"
    }
