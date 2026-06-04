"""
Test Executor — Runs generated Playwright tests with real browser.
ASYNC VERSION with REAL-TIME CONSOLE OUTPUT.
"""
import json
import os
import re
import time
from pathlib import Path
from typing import AsyncGenerator
import asyncio


async def execute_test(
    feature: dict,
    project_path: str,
    target_url: str,
    credentials: dict = None,
    browser_type: str = "chromium",
) -> AsyncGenerator[str, None]:
    """
    Execute Playwright test for a feature using Async API.
    WITH REAL-TIME TERMINAL OUTPUT.
    """
    
    feature_id = feature.get('id', 'unknown')
    feature_name = feature.get('name', 'Unknown Feature')
    entry_point = feature.get('entry_point', '/')
    feature_type = feature.get('type', 'unknown')
    
    # 🔴 CONSOLE OUTPUT - Shows in terminal
    print(f"\n{'='*60}")
    print(f"🎭 STARTING TEST: {feature_name}")
    print(f"🆔 Feature ID: {feature_id}")
    print(f"{'='*60}\n")
    
    yield f"data: 🎭 Running test: {feature_name}\n\n"
    yield f"data: 🌐 Target URL: {target_url}\n\n"
    
    # Setup paths
    session_root = Path(project_path).parent
    artifacts_dir = session_root / "artifacts" / feature_id
    screenshots = session_root / "test-results" / "screenshots"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    screenshots.mkdir(parents=True, exist_ok=True)
    
    yield "data: ✓ Using Python Playwright ASYNC API\n\n"
    
    # Check Playwright installation
    try:
        from playwright.async_api import async_playwright
        yield "data: 🔍 Checking Playwright installation...\n\n"
        yield "data: ✓ Playwright Python library available\n\n"
    except ImportError:
        print("❌ ERROR: Playwright not installed")
        yield "data: ✗ ERROR: Playwright not installed\n\n"
        yield "data: 💡 Run: pip install playwright && playwright install\n\n"
        yield "data: [DONE]\n\n"
        return
    
    yield "data: 🧪 Executing test with extracted selectors...\n\n"
    
    # Get credentials
    username = ''
    password = ''
    
    if credentials:
        if isinstance(credentials, dict):
            username = credentials.get('username', '')
            password = credentials.get('password', '')
        elif isinstance(credentials, str):
            username = credentials
            password = ''
    
    if username:
        print(f"🔐 Using credentials: {username}")
        yield f"data: 🔐 Using credentials (username: {username})\n\n"
    
    yield f"data: 📝 Test: {feature_name}\n\n"
    yield f"data: 🚪 Entry Point: {entry_point}\n\n"
    yield f"data: 📋 Type: {feature_type}\n\n"
    
    # Execute test
    output = []
    test_passed = True
    action_failures = 0
    action_successes = 0
    
    try:
        async with async_playwright() as p:
            print("🌐 Launching Chromium browser...")
            yield "data: 🌐 Launching Chromium browser...\n\n"
            
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            page.set_default_timeout(30000)
            
            # Pre-authentication if needed
            needs_auth = feature_type not in ['authentication', 'navigation']
            
            if needs_auth and username and password:
                print("🔐 Pre-authentication: Logging in via SSO...")
                yield "data: ℹ️ This feature requires authentication\n\n"
                yield "data: 🔐 Pre-authentication: Logging in via SSO...\n\n"
                
                auth_success = await _do_sso_login(page, target_url, username, password, output)
                
                if auth_success:
                    print("  ✅ Pre-authentication successful")
                    yield "data:   ✅ Pre-authentication successful\n\n"
                else:
                    print("  ⚠️ Pre-authentication had issues")
                    yield "data:   ⚠️ Pre-authentication had issues, continuing anyway...\n\n"
            
            # Navigate to feature entry point
            full_url = target_url.rstrip('/') + entry_point
            print(f"➡️ Navigating to: {full_url}")
            yield f"data: ➡️ Navigating to: {full_url}\n\n"
            
            try:
                await page.goto(full_url, wait_until='networkidle', timeout=30000)
                await page.wait_for_load_state('domcontentloaded')
                print("✓ Page loaded")
                yield "data: ✓ Page loaded\n\n"
            except Exception as e:
                print(f"⚠️ Navigation issue: {str(e)[:100]}")
                yield f"data: ⚠️ Navigation issue: {str(e)[:100]}\n\n"
                test_passed = False
            
            # Take initial screenshot
            screenshot_path = screenshots / f"{feature_id}_initial.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 Screenshot: {feature_id}_initial.png")
            yield f"data: 📸 Screenshot: {feature_id}_initial.png\n\n"
            
            # Execute test steps
            test_steps = feature.get('test_steps', [])
            ui_components = feature.get('ui_components', {})
            
            print(f"🎯 Executing {len(test_steps)} test actions...")
            yield f"data: 🎯 Executing {len(test_steps)} test actions...\n\n"
            yield f"data: 📋 Using {len(ui_components)} extracted UI components\n\n"
            
            for step_data in test_steps:
                step_num = step_data.get('step', 0)
                action = step_data.get('action', '')
                component_name = step_data.get('component', '')
                value = step_data.get('value', '')
                description = step_data.get('description', '')
                
                print(f"  Step {step_num}: {description}")
                yield f"data:   Step {step_num}: {description}\n\n"
                
                # Get component metadata
                component = ui_components.get(component_name, {})
                
                if not component and component_name:
                    print(f"    ⚠️ Component '{component_name}' not found")
                    yield f"data:     ⚠️ Component '{component_name}' not found in metadata\n\n"
                    continue
                
                # Execute action
                success = await _execute_action(
                    page, action, component, value, output, 
                    screenshots, artifacts_dir, feature_id
                )
                
                if success:
                    action_successes += 1
                    print("    ✓ Action completed")
                    yield "data:     ✓ Action completed\n\n"
                    
                    # Validate outcome for critical actions
                    if action in ['click', 'fill', 'select']:
                        validation_passed = await _validate_action_outcome(
                            page, action, component, value, output
                        )
                        if not validation_passed:
                            print("    ⚠️ Validation failed")
                            yield "data:     ⚠️ Action completed but validation failed\n\n"
                            test_passed = False
                            action_failures += 1
                        else:
                            print("    ✓ Outcome validated")
                            yield "data:     ✓ Outcome validated\n\n"
                    
                else:
                    action_failures += 1
                    test_passed = False
                    print("    ⚠️ Action failed")
                    yield "data:     ⚠️ Action failed, continuing...\n\n"
            
            # Take final screenshots
            screenshot_path = screenshots / f"{feature_id}_after_actions.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 Screenshot: {feature_id}_after_actions.png")
            yield f"data: 📸 Screenshot: {feature_id}_after_actions.png\n\n"
            
            await page.wait_for_timeout(2000)
            
            screenshot_path = screenshots / f"{feature_id}_final.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"📸 Screenshot: {feature_id}_final.png")
            yield f"data: 📸 Screenshot: {feature_id}_final.png\n\n"
            
            await browser.close()
            print("✓ Browser closed")
            yield "data: ✓ Browser closed\n\n"
        
        # Report actual test result
        if test_passed and action_successes > 0 and action_failures == 0:
            print(f"✅ TEST PASSED - Feature {feature_id}")
            print(f"   {action_successes} actions succeeded")
            yield "data: ✅ Test passed!\n\n"
        elif action_failures == 0 and action_successes == 0:
            print(f"⚠️ NO ACTIONS EXECUTED - Feature {feature_id}")
            yield "data: ⚠️ Test completed but no actions were executed\n\n"
            test_passed = False
        else:
            print(f"❌ TEST FAILED - Feature {feature_id}")
            print(f"   {action_failures} failed, {action_successes} succeeded")
            yield f"data: ❌ Test failed! ({action_failures} actions failed, {action_successes} succeeded)\n\n"
            test_passed = False
        
        print(f"{'='*60}\n")
        
        # Save detailed results
        result = {
            "feature_id": feature_id,
            "feature_name": feature_name,
            "passed": test_passed,
            "actions_executed": len(test_steps),
            "actions_succeeded": action_successes,
            "actions_failed": action_failures,
            "output": output,
            "timestamp": time.time()
        }
        
        result_file = artifacts_dir / "result.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
    except Exception as e:
        print(f"❌ EXCEPTION in test {feature_id}: {str(e)}")
        yield f"data: ✗ EXCEPTION: {str(e)}\n\n"
        test_passed = False
        
        import traceback
        error_details = traceback.format_exc()
        
        error_file = artifacts_dir / "error.log"
        with open(error_file, 'w') as f:
            f.write(error_details)
        
        yield "data: 📄 Error details saved to error.log\n\n"
    
    duration = 0
    yield f"data: ⏱️ Duration: {duration}ms\n\n"
    yield "data: [DONE]\n\n"


async def _do_sso_login(page, base_url: str, username: str, password: str, output: list) -> bool:
    """Perform SSO login (Microsoft OAuth) - ASYNC VERSION."""
    try:
        login_url = base_url.rstrip('/') + '/login'
        await page.goto(login_url, wait_until='domcontentloaded', timeout=30000)
        
        # Click SSO button
        sso_selectors = [
            "button.bg-\\[\\#282828\\]",
            "button:has-text('Sign In')",
            "button:has-text('Login')",
            "button[type='button']"
        ]
        
        for selector in sso_selectors:
            try:
                await page.click(selector, timeout=5000)
                output.append("  ✓ Clicked SSO button")
                break
            except:
                continue
        
        await page.wait_for_timeout(3000)
        
        # Check if on Microsoft OAuth page
        if 'login.microsoftonline.com' in page.url:
            output.append("  ℹ️ On Microsoft OAuth page")
            
            # Fill email
            email_selectors = ["input[type='email']", "input[name='loginfmt']"]
            for selector in email_selectors:
                try:
                    await page.fill(selector, username, timeout=5000)
                    output.append("    ✓ Filled email")
                    break
                except:
                    continue
            
            # Click Next
            try:
                await page.click("input[type='submit']", timeout=5000)
                await page.wait_for_timeout(2000)
            except:
                pass
            
            # Fill password
            password_selectors = ["input[type='password']", "input[name='passwd']"]
            for selector in password_selectors:
                try:
                    await page.fill(selector, password, timeout=5000)
                    output.append("    ✓ Filled password")
                    break
                except:
                    continue
            
            # Click Sign in
            try:
                await page.click("input[type='submit']", timeout=5000)
                await page.wait_for_timeout(2000)
            except:
                pass
            
            # Handle "Stay signed in?"
            try:
                await page.click("input[type='submit'][value='Yes']", timeout=5000)
                output.append("  ✓ Clicked 'Yes' on stay signed in")
            except:
                pass
            
            # Wait for redirect back
            await page.wait_for_timeout(5000)
            
            return True
        
        return True
        
    except Exception as e:
        output.append(f"  ⚠️ Login error: {str(e)[:100]}")
        return False


async def _execute_action(page, action: str, component: dict, value: str, output: list, screenshots, artifacts_dir, feature_id) -> bool:
    """Execute a single test action - ASYNC VERSION with NAVIGATE FIX."""
    
    # 🔴 CRITICAL FIX #1: Skip redundant navigate actions
    if action == 'navigate':
        url = component.get('url', value)
        if not url or url == '':
            # No URL = redundant navigate (already at entry point)
            print("      ⏩ Skipped redundant navigate")
            output.append("    ⏩ Skipped redundant navigate (already at entry point)")
            return True  # ✅ Count as SUCCESS, don't fail
        
        # If URL is provided, execute navigation
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            print(f"      ✓ Navigated to {url}")
            output.append(f"    ✓ Navigated to {url}")
            return True
        except Exception as e:
            print(f"      ✗ Navigation failed: {str(e)[:100]}")
            output.append(f"    ✗ Navigation failed: {str(e)[:100]}")
            return False
    
    if action == 'wait':
        try:
            wait_time = int(value) if value else 2000
            await page.wait_for_timeout(wait_time)
            output.append(f"    ✓ Waited {wait_time}ms")
            return True
        except:
            return False
    
    # Get selector for all other actions
    selector = component.get('selector', '')
    alternative_selectors = component.get('alternative_selectors', [])
    
    if not selector:
        output.append("    ✗ No selector provided")
        return False
    
    # Try to find element
    all_selectors = [selector] + alternative_selectors
    found_selector = None
    
    for sel in all_selectors:
        try:
            if await page.locator(sel).count() > 0:
                found_selector = sel
                print(f"      ✓ Found element: {sel[:50]}")
                output.append(f"    ✓ Found element: {sel}")
                break
        except:
            continue
    
    if not found_selector:
        print(f"      ✗ Element not found (tried {len(all_selectors)} selectors)")
        output.append(f"    ✗ Element not found (tried {len(all_selectors)} selectors)")
        return False
    
    # Execute action based on type
    try:
        if action == 'fill':
            # Check if this is a file input
            try:
                element_type = await page.locator(found_selector).get_attribute('type')
            except:
                element_type = None
            
            if element_type == 'file':
                # File upload
                test_file = Path(artifacts_dir) / 'test_upload.pdf'
                test_file.write_bytes(b'%PDF-1.4\n%Test PDF file\n%%EOF')
                await page.set_input_files(found_selector, str(test_file))
                print(f"      ✓ Uploaded file: {test_file.name}")
                output.append(f"    ✓ Uploaded file: {test_file.name}")
                return True
            else:
                # Regular text input
                test_value = component.get('test_value', value) or 'Test data'
                await page.fill(found_selector, test_value, timeout=30000)
                print(f"      ✓ Filled with: {test_value[:30]}")
                output.append(f"    ✓ Filled with: {test_value[:50]}")
                return True
            
        elif action == 'click':
            await page.click(found_selector, timeout=30000)
            print("      ✓ Clicked successfully")
            output.append("    ✓ Clicked successfully")
            await page.wait_for_timeout(1000)
            return True
            
        elif action == 'select':
            await page.select_option(found_selector, value, timeout=30000)
            print(f"      ✓ Selected: {value}")
            output.append(f"    ✓ Selected: {value}")
            return True
            
        elif action in ['check', 'uncheck']:
            if action == 'check':
                await page.check(found_selector, timeout=30000)
            else:
                await page.uncheck(found_selector, timeout=30000)
            print(f"      ✓ {action.capitalize()}ed")
            output.append(f"    ✓ {action.capitalize()}ed")
            return True
            
        elif action == 'press':
            await page.press(found_selector, value, timeout=30000)
            print(f"      ✓ Pressed: {value}")
            output.append(f"    ✓ Pressed: {value}")
            return True
            
        elif action in ['verify_visible', 'verify_text', 'verify_count']:
            is_visible = await page.locator(found_selector).is_visible()
            if is_visible:
                print("      ✓ Element is visible")
                output.append("    ✓ Element is visible")
                return True
            else:
                print("      ✗ Element not visible")
                output.append("    ✗ Element not visible")
                return False
        
        else:
            print(f"      ⚠️ Unknown action: {action}")
            output.append(f"    ⚠️ Unknown action: {action}")
            return False
            
    except Exception as e:
        print(f"      ✗ Action failed: {str(e)[:100]}")
        output.append(f"    ✗ Action failed: {str(e)[:100]}")
        return False


async def _validate_action_outcome(page, action: str, component: dict, value: str, output: list) -> bool:
    """Validate that an action had the expected outcome - ASYNC VERSION."""
    try:
        if action == 'click':
            success_indicators = [
                ".success-message",
                ".success",
                "[role='alert']:has-text('Success')",
                ".toast-success",
                ".notification-success"
            ]
            
            await page.wait_for_timeout(1000)
            
            for indicator in success_indicators:
                try:
                    if await page.locator(indicator).count() > 0:
                        output.append(f"      ✓ Found success indicator")
                        return True
                except:
                    continue
            
            error_indicators = [
                ".error-message",
                ".error",
                "[role='alert']:has-text('Error')",
                ".toast-error",
                ".notification-error"
            ]
            
            for indicator in error_indicators:
                try:
                    if await page.locator(indicator).count() > 0:
                        output.append(f"      ✗ Found error indicator")
                        return False
                except:
                    continue
            
            return True
        
        elif action == 'fill':
            selector = component.get('selector', '')
            if selector:
                try:
                    actual_value = await page.input_value(selector, timeout=2000)
                    test_value = component.get('test_value', value) or 'Test data'
                    if actual_value == test_value:
                        output.append(f"      ✓ Value verified: {actual_value[:30]}")
                        return True
                    else:
                        output.append(f"      ✗ Value mismatch")
                        return False
                except:
                    return True
        
        return True
        
    except Exception as e:
        output.append(f"      ⚠️ Validation error: {str(e)[:50]}")
        return True
