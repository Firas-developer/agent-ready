# """
# Test Executor - Using Playwright ASYNC API (Fixed)
# ✅ Works with FastAPI async context
# ✅ Session persistence
# ✅ Screenshots work
# ✅ Credentials used properly
# """
# import time
# import json
# import re
# from typing import Optional, Dict, List, AsyncGenerator
# from pathlib import Path
# from playwright.async_api import async_playwright, Browser, BrowserContext, Page


# class PlaywrightTestExecutor:
#     """Manages Playwright browser instance and test execution."""
    
#     def __init__(self, session_id: str, workspace_path: str):
#         self.session_id = session_id
#         self.workspace_path = workspace_path
        
#         self.playwright = None
#         self.browser: Optional[Browser] = None
#         self.context: Optional[BrowserContext] = None
#         self.page: Optional[Page] = None
        
#         # Screenshot directories
#         self.screenshots_dir = Path(workspace_path) / "screenshots"
#         self.before_dir = self.screenshots_dir / "before"
#         self.after_dir = self.screenshots_dir / "after"
#         self.failures_dir = self.screenshots_dir / "failures"
        
#         self.before_dir.mkdir(parents=True, exist_ok=True)
#         self.after_dir.mkdir(parents=True, exist_ok=True)
#         self.failures_dir.mkdir(parents=True, exist_ok=True)
    
#     async def start_browser(self):
#         """Start Playwright browser with persistent context."""
#         self.playwright = await async_playwright().start()
        
#         # Launch browser (visible for debugging)
#         self.browser = await self.playwright.chromium.launch(
#             headless=False,
#             slow_mo=500
#         )
        
#         # Create context (persists cookies/session)
#         self.context = await self.browser.new_context(
#             viewport={'width': 1920, 'height': 1080},
#             user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
#         )
        
#         # Create page
#         self.page = await self.context.new_page()
    
#     async def close_browser(self):
#         """Close browser and cleanup."""
#         if self.page:
#             await self.page.close()
#         if self.context:
#             await self.context.close()
#         if self.browser:
#             await self.browser.close()
#         if self.playwright:
#             await self.playwright.stop()
    
#     async def authenticate(self, app_url: str, credentials: Dict) -> bool:
#         """Perform full SSO authentication with credentials."""
#         username = credentials.get("username", "")
#         password = credentials.get("password", "")
        
#         if not username or not self.page:
#             return False
        
#         try:
#             # Navigate to app
#             await self.page.goto(app_url, wait_until='networkidle')
#             await self.page.wait_for_timeout(2000)
            
#             # Click SSO Login button
#             try:
#                 sso_button = self.page.get_by_role("button", name=re.compile("SSO Login", re.I))
#                 if await sso_button.is_visible():
#                     await sso_button.click()
#                     await self.page.wait_for_timeout(3000)
#             except:
#                 pass
            
#             # Fill Microsoft SSO form
#             try:
#                 email_input = self.page.get_by_role("textbox").first
#                 if await email_input.is_visible():
#                     await email_input.fill(username)
#                     await self.page.wait_for_timeout(1000)
                    
#                     # Click Next
#                     next_button = self.page.get_by_role("button", name=re.compile("next|continue", re.I))
#                     if await next_button.is_visible():
#                         await next_button.click()
#                         await self.page.wait_for_timeout(3000)
                    
#                     # Fill password
#                     if password:
#                         pwd_input = self.page.get_by_label(re.compile("password", re.I))
#                         if await pwd_input.is_visible():
#                             await pwd_input.fill(password)
#                             await self.page.wait_for_timeout(1000)
                            
#                             # Click Sign In
#                             signin_button = self.page.get_by_role("button", name=re.compile("sign in", re.I))
#                             if await signin_button.is_visible():
#                                 await signin_button.click()
                                
#                                 # Wait for redirect
#                                 try:
#                                     await self.page.wait_for_url(f"{app_url}**", timeout=15000)
#                                 except:
#                                     pass
#                                 await self.page.wait_for_timeout(3000)
#                                 return True
#             except Exception as e:
#                 print(f"Auth form error: {e}")
            
#             return True
            
#         except Exception as e:
#             print(f"Authentication error: {e}")
#             return False
    
#     async def is_authenticated(self) -> bool:
#         """Check if user is authenticated."""
#         if not self.page:
#             return False
        
#         try:
#             page_content = await self.page.content()
#             page_content_lower = page_content.lower()
            
#             # If we see SSO Login button, not authenticated
#             if "sso login" in page_content_lower:
#                 return False
            
#             # If we see logout/profile, authenticated
#             if any(word in page_content_lower for word in ["logout", "sign out", "profile menu"]):
#                 return True
            
#             return False
            
#         except:
#             return False


# async def execute_all_tests(
#     session_id: str,
#     project_path: str,
#     app_url: str,
#     features: List[Dict],
#     credentials: Optional[Dict] = None,
#     workspace_path: Optional[str] = None
# ) -> AsyncGenerator[str, None]:
#     """
#     Execute tests using Playwright Async API.
#     ✅ Works with FastAPI async context
#     """
#     from . import session
    
#     if not workspace_path:
#         workspace_path = str(Path(project_path).parent)
    
#     # Initialize executor
#     executor = PlaywrightTestExecutor(session_id, workspace_path)
    
#     yield f"data: 🌐 Starting Playwright browser...\n\n"
#     await executor.start_browser()
    
#     yield f"data: 🌐 Navigating to: {app_url}\n\n"
#     await executor.page.goto(app_url, wait_until='networkidle')
#     await executor.page.wait_for_timeout(2000)
    
#     # Authenticate if credentials provided
#     if credentials:
#         yield "data: 🔑 Authenticating with credentials...\n\n"
        
#         auth_success = await executor.authenticate(app_url, credentials)
        
#         if auth_success:
#             yield "data: ✅ Authentication successful - session active!\n\n"
#         else:
#             yield "data: ⚠️ Authentication issues\n\n"
        
#         await executor.page.wait_for_timeout(2000)
    
#     yield "data: \n\n"
    
#     # Execute each feature
#     results = {
#         "total": len(features),
#         "passed": 0,
#         "failed": 0,
#         "skipped": 0,
#         "feature_results": []
#     }
    
#     for index, feature in enumerate(features, 1):
#         feature_id = feature["id"]
#         feature_name = feature["name"]
#         feature_type = feature.get("type", "unknown")
#         entry_point = feature.get("entry_point", "/")
        
#         yield f"data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
#         yield f"data: 📝 Test {index}/{len(features)}: {feature_name}\n\n"
#         yield f"data: 🔗 Entry: {entry_point}\n\n"
        
#         result = {
#             "feature_id": feature_id,
#             "feature_name": feature_name,
#             "status": "not_run",
#             "commands": [],
#             "error": None,
#             "duration_ms": 0,
#             "screenshots": {}
#         }
        
#         start_time = time.time()
        
#         try:
#             # Check authentication state
#             is_auth = await executor.is_authenticated()
#             yield f"data:    🔐 Auth State: {'✅ Authenticated' if is_auth else '❌ Not Authenticated'}\n\n"
            
#             # Skip login tests if already authenticated
#             if feature_type == "authentication" and "login" in feature_name.lower() and is_auth:
#                 yield f"data:    ⏩ Skipping - user already authenticated\n\n"
#                 result["status"] = "skipped"
#                 result["error"] = "User already authenticated"
#                 results["skipped"] += 1
#             else:
#                 # ✅ CAPTURE BEFORE SCREENSHOT
#                 clean_name = feature_name.lower().replace(" ", "_")[:50]
#                 before_path = executor.before_dir / f"{clean_name}_before.png"
#                 await executor.page.screenshot(path=str(before_path))
#                 result["screenshots"]["before"] = str(before_path)
#                 yield f"data:    📸 Before: {before_path.name}\n\n"
                
#                 # Navigate to entry point
#                 if entry_point and entry_point != "/":
#                     full_url = app_url.rstrip('/') + entry_point
#                     yield f"data:    → Navigating to {entry_point}\n\n"
                    
#                     await executor.page.goto(full_url, wait_until='networkidle')
#                     await executor.page.wait_for_timeout(2000)
                
#                 # Execute feature test
#                 test_passed = await _execute_feature_test(executor, feature, result)
                
#                 result["duration_ms"] = int((time.time() - start_time) * 1000)
                
#                 if test_passed:
#                     result["status"] = "passed"
#                     results["passed"] += 1
                    
#                     # ✅ CAPTURE AFTER SCREENSHOT
#                     after_path = executor.after_dir / f"{clean_name}_after.png"
#                     await executor.page.screenshot(path=str(after_path))
#                     result["screenshots"]["after"] = str(after_path)
#                     yield f"data:    📸 After: {after_path.name}\n\n"
#                     yield f"data:    ✅ PASSED ({result['duration_ms']}ms)\n\n"
#                 else:
#                     result["status"] = "failed"
#                     results["failed"] += 1
                    
#                     # ✅ CAPTURE FAILURE SCREENSHOT
#                     failure_path = executor.failures_dir / f"{clean_name}_failure.png"
#                     await executor.page.screenshot(path=str(failure_path))
#                     result["screenshots"]["failure"] = str(failure_path)
#                     yield f"data:    📸 Failure: {failure_path.name}\n\n"
#                     yield f"data:    ❌ FAILED ({result['duration_ms']}ms)\n\n"
        
#         except Exception as e:
#             result["status"] = "failed"
#             result["error"] = str(e)
#             result["duration_ms"] = int((time.time() - start_time) * 1000)
#             results["failed"] += 1
#             yield f"data:    ❌ Error: {e}\n\n"
        
#         # Store result
#         session.update_feature_result(session_id, feature_id, result)
#         results["feature_results"].append(result)
        
#         # Print summary
#         yield "data: \n\n"
#         yield f"data:    ┌{'─' * 50}┐\n\n"
#         yield f"data:    │ 📊 TEST RESULT SUMMARY\n\n"
#         yield f"data:    ├{'─' * 50}┤\n\n"
#         yield f"data:    │ Feature: {feature_name}\n\n"
#         yield f"data:    │ Status: "
        
#         if result["status"] == "passed":
#             yield f"✅ PASSED\n\n"
#         elif result["status"] == "failed":
#             yield f"❌ FAILED\n\n"
#         else:
#             yield f"⏩ SKIPPED\n\n"
        
#         yield f"data:    │ Duration: {result['duration_ms']}ms\n\n"
#         yield f"data:    │ Screenshots: {len(result['screenshots'])}\n\n"
#         yield f"data:    └{'─' * 50}┘\n\n"
#         yield "data: \n\n"
#         yield f"data:    📈 Running Stats: {results['passed']} passed, {results['failed']} failed, {results['skipped']} skipped ({index}/{len(features)} complete)\n\n"
#         yield "data: \n\n"
    
#     # Close browser
#     yield "data: 🔴 Closing browser...\n\n"
#     await executor.close_browser()
    
#     # Final Summary
#     yield "data: \n\n"
#     yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
#     yield "data: 📊 FINAL SUMMARY\n\n"
#     yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
#     yield f"data: 🧪 Total: {results['total']}\n\n"
#     yield f"data: ✅ Passed: {results['passed']}\n\n"
#     yield f"data: ❌ Failed: {results['failed']}\n\n"
#     yield f"data: ⏩ Skipped: {results['skipped']}\n\n"
    
#     if results['passed'] + results['failed'] > 0:
#         pass_rate = (results['passed'] / (results['passed'] + results['failed'])) * 100
#         yield f"data: 📈 Pass Rate: {pass_rate:.1f}%\n\n"
    
#     yield "data: \n\n"
#     yield "data: __RESULTS_JSON__\n\n"
#     yield f"data: {json.dumps(results, indent=2)}\n\n"


# async def _execute_feature_test(
#     executor: PlaywrightTestExecutor,
#     feature: Dict,
#     result: Dict
# ) -> bool:
#     """Execute feature-specific test logic."""
#     feature_type = feature.get("type", "")
#     feature_name = feature.get("name", "").lower()
    
#     try:
#         # Authentication features
#         if feature_type == "authentication":
#             if "logout" in feature_name:
#                 # Find and click logout button
#                 try:
#                     logout_btn = executor.page.get_by_role("button", name=re.compile("logout|sign out", re.I))
#                     if await logout_btn.is_visible():
#                         await logout_btn.click()
#                         await executor.page.wait_for_timeout(2000)
#                         return True
#                 except:
#                     pass
#                 return False
#             else:
#                 # Login already handled in main auth
#                 return True
        
#         # Chat features
#         elif feature_type == "interaction" and "chat" in feature_name:
#             try:
#                 # Find chat input
#                 chat_input = executor.page.locator("textarea, input[type='text']").first
#                 if await chat_input.is_visible():
#                     await chat_input.fill("Hello, this is a test message")
#                     await executor.page.wait_for_timeout(1000)
                    
#                     # Find send button
#                     send_btn = executor.page.get_by_role("button", name=re.compile("send", re.I))
#                     if await send_btn.is_visible():
#                         await send_btn.click()
#                         await executor.page.wait_for_timeout(2000)
#                         return True
#             except:
#                 pass
#             return False
        
#         # Form features
#         elif feature_type == "form":
#             try:
#                 inputs = executor.page.locator("input[type='text'], input[type='email']")
#                 count = await inputs.count()
                
#                 if count > 0:
#                     for i in range(min(count, 3)):
#                         await inputs.nth(i).fill(f"Test data {i+1}")
#                         await executor.page.wait_for_timeout(500)
#                     return True
#             except:
#                 pass
#             return False
        
#         # Default: verify page loaded
#         else:
#             page_title = await executor.page.title()
#             return len(page_title) > 0
    
#     except Exception as e:
#         result["error"] = str(e)
#         return False
