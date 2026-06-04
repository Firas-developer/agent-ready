"""
Test Generator — AI generates Playwright tests from detected features.
Enhanced with larger file reading and better context.
"""
import re
from pathlib import Path
from typing import AsyncGenerator
import asyncio


async def generate_test(
    feature: dict,
    project_path: str,
    provider: str,
    model: str = None,
) -> AsyncGenerator[str, None]:
    """
    Generate Playwright test for a specific feature.
    Yields SSE progress messages and test code.
    """
    
    yield f"data: 🎯 Generating test for: {feature['name']}\n\n"
    yield f"data: 📋 Type: {feature.get('type', 'unknown')}\n\n"
    yield f"data: 🚪 Entry point: {feature.get('entry_point', '/')}\n\n"
    
    # Step 1: Load source files with ROBUST path resolution
    yield "data: 📄 Reading source files for AI context...\n\n"
    
    root = Path(project_path)
    source_files = feature.get('detected_from', [])
    
    code_context = []
    files_read = 0
    
    if not source_files:
        yield "data: ℹ️ No source files specified in feature metadata\n\n"
    else:
        yield f"data: 🔍 Attempting to read {len(source_files)} source files...\n\n"
    
    for file_path in source_files[:5]:  # Limit to 5 files for performance
        clean_path = file_path
        
        # STRATEGY 1: Clean known prefixes
        prefixes_to_remove = [
            'zip/', 'zip\\',
            'project/', 'project\\', 
            './', '.\\',
            'uploads/', 'uploads\\',
            'backend/uploads/', 'backend\\uploads\\',
        ]
        
        for prefix in prefixes_to_remove:
            if clean_path.startswith(prefix):
                clean_path = clean_path[len(prefix):]
        
        yield f"data: 🔎 Looking for: {clean_path}\n\n"
        
        full_path = None
        
        # STRATEGY 2: Direct path from root
        candidate = root / clean_path
        if candidate.exists() and candidate.is_file():
            full_path = candidate
            yield f"data: ✓ Found via direct path\n\n"
        
        # STRATEGY 3: Try removing first directory level
        if not full_path:
            parts = Path(clean_path).parts
            if len(parts) > 1:
                alt_path = root / Path(*parts[1:])
                if alt_path.exists() and alt_path.is_file():
                    full_path = alt_path
                    yield f"data: ✓ Found by removing first directory level\n\n"
        
        # STRATEGY 4: Recursive search for filename
        if not full_path:
            file_name = Path(clean_path).name
            yield f"data: 🔍 Searching recursively for: {file_name}\n\n"
            
            found_candidates = list(root.rglob(file_name))
            
            if found_candidates:
                best_match = None
                clean_suffix = str(Path(clean_path)).replace('\\', '/')
                
                for candidate in found_candidates:
                    candidate_str = str(candidate).replace('\\', '/')
                    if candidate_str.endswith(clean_suffix):
                        best_match = candidate
                        yield f"data: ✓ Exact suffix match found!\n\n"
                        break
                
                if not best_match:
                    best_match = min(found_candidates, key=lambda p: len(str(p)))
                    yield f"data: ✓ Using closest match (shortest path)\n\n"
                
                full_path = best_match
            else:
                yield f"data: ⚠️ No files found with name '{file_name}'\n\n"
        
        # STRATEGY 5: Debug output
        if not full_path or not full_path.exists():
            yield f"data: ⚠️ FAILED to find: {clean_path}\n\n"
            yield f"data: 📂 Checked paths:\n\n"
            yield f"data:   1. Direct: {root / clean_path}\n\n"
            
            if len(Path(clean_path).parts) > 1:
                yield f"data:   2. Without first dir: {root / Path(*Path(clean_path).parts[1:])}\n\n"
            
            yield f"data:   3. Recursive search for: {Path(clean_path).name}\n\n"
            
            # Show sample files
            yield f"data: 💡 Sample files in project root:\n\n"
            sample_tsx = list(root.rglob("*.tsx"))[:5]
            sample_jsx = list(root.rglob("*.jsx"))[:5]
            
            for i, sample in enumerate(sample_tsx + sample_jsx, 1):
                try:
                    rel = sample.relative_to(root)
                    yield f"data:      - {rel}\n\n"
                except:
                    pass
            
            yield "data: \n\n"
            continue
        
        # FILE FOUND - Read it with INCREASED size limit
        try:
            content = full_path.read_text(encoding='utf-8', errors='ignore')
            
            # INCREASED: 2000 → 5000 → 15000 chars to capture more selector context
            if len(content) > 15000:
                truncated_content = content[:15000]
                yield f"data: ℹ️ File truncated from {len(content)} to 15000 chars\n\n"
            else:
                truncated_content = content
            
            code_context.append(
                f"\n## File: {clean_path}\n"
                f"```\n{truncated_content}\n```\n"
            )
            files_read += 1
            
            yield f"data: ✅ Successfully read {clean_path} ({len(content)} chars)\n\n"
            
        except UnicodeDecodeError:
            yield f"data: ⚠️ Skipped (binary file): {clean_path}\n\n"
        except PermissionError:
            yield f"data: ⚠️ Skipped (permission denied): {clean_path}\n\n"
        except Exception as e:
            yield f"data: ⚠️ Error reading {clean_path}: {str(e)[:100]}\n\n"
    
    # Summary
    if files_read == 0:
        yield "data: ⚠️ WARNING: No source files could be read\n\n"
        yield "data: 💡 AI will generate generic test without source code context\n\n"
        code_context.append(
            "\n## Source Code Context\n"
            "(No source code available - generate test based on feature description and type only)\n"
        )
    else:
        yield f"data: ✅ Successfully read {files_read}/{len(source_files)} source files\n\n"
    
    yield "data: \n\n"
    
    # Step 2: Build context for LLM
    ui_components = feature.get('ui_components', {})
    test_steps = feature.get('test_steps', [])
    
    context = f"""## Feature Details

**Name**: {feature['name']}
**Type**: {feature.get('type', 'unknown')}
**Priority**: {feature.get('priority', 'medium')}
**Entry Point**: {feature.get('entry_point', '/')}
**Description**: {feature.get('description', 'No description')}

## Extracted UI Components ({len(ui_components)} total)
{_format_ui_components(ui_components)}

## Test Steps ({len(test_steps)} total)
{_format_test_steps(test_steps)}

## Source Code Context
{"".join(code_context)}
"""
    
    yield "data: 🤖 Calling AI to generate Playwright test...\n\n"
    
    # Step 3: Load prompt template
    prompt_file = Path(__file__).parent.parent.parent / "prompts" / "test_generation.txt"
    
    if not prompt_file.exists():
        yield "data: ✗ ERROR: test_generation.txt prompt not found\n\n"
        yield "data: 🔄 Using fallback test generation...\n\n"
        
        test_code = _generate_fallback_test(feature)
        
        yield "data: __TEST_CODE_START__\n\n"
        yield f"data: {test_code}\n\n"
        yield "data: __TEST_CODE_END__\n\n"
        yield "data: [DONE]\n\n"
        return
    
    system_prompt = prompt_file.read_text(encoding='utf-8')
    
    user_prompt = f"""Generate a complete Playwright test for this feature:

{context}

IMPORTANT INSTRUCTIONS:
1. Use the EXACT selectors from the ui_components section
2. Follow the test_steps sequence provided
3. Include proper assertions to verify success
4. Add error handling for flaky elements
5. Use TypeScript with proper types
6. Set timeouts to 30000ms (30 seconds)
7. Add validation after each critical action (click, fill, submit)

Output the complete .spec.ts file ready to run.
"""
    
    # Step 4: Call LLM
    try:
        from llm.client import LLMClient
        
        client = LLMClient(provider=provider, model=model)
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.complete(system_prompt, user_prompt, max_tokens=3072)
        )
        
        yield "data: ✓ AI generated test code\n\n"
        
        # Step 5: Extract and validate
        test_code = _extract_test_code(response)
        
        if not test_code:
            yield "data: ✗ Failed to extract valid test code\n\n"
            yield "data: 🔄 Creating fallback test...\n\n"
            test_code = _generate_fallback_test(feature)
        else:
            # Validate
            validation_errors = []
            
            if "import {" not in test_code:
                validation_errors.append("Missing imports")
            if "test.describe" not in test_code and "test(" not in test_code:
                validation_errors.append("Missing test structure")
            if "expect(" not in test_code:
                validation_errors.append("Missing assertions")
            
            if validation_errors:
                yield f"data: ⚠️ Generated test has issues: {', '.join(validation_errors)}\n\n"
                yield "data: 🔄 Using fallback test instead\n\n"
                test_code = _generate_fallback_test(feature)
        
        yield f"data: 📝 Generated {len(test_code)} chars of test code\n\n"
        
        yield "data: __TEST_CODE_START__\n\n"
        yield f"data: {test_code}\n\n"
        yield "data: __TEST_CODE_END__\n\n"
        
    except Exception as e:
        yield f"data: ✗ Error calling LLM: {str(e)[:200]}\n\n"
        
        test_code = _generate_fallback_test(feature)
        yield "data: 🔄 Using fallback test\n\n"
        yield "data: __TEST_CODE_START__\n\n"
        yield f"data: {test_code}\n\n"
        yield "data: __TEST_CODE_END__\n\n"
    
    yield "data: [DONE]\n\n"


def _format_ui_components(ui_components: dict) -> str:
    """Format ui_components dict for prompt."""
    if not ui_components:
        return "(No UI components detected - AI should generate basic navigation test)"
    
    lines = []
    for component_name, component_data in ui_components.items():
        selector = component_data.get('selector', 'N/A')
        action = component_data.get('action', 'click')
        comp_type = component_data.get('type', 'element')
        
        lines.append(f"- **{component_name}** ({comp_type})")
        lines.append(f"  - Selector: `{selector}`")
        lines.append(f"  - Action: {action}")
        
        alt_selectors = component_data.get('alternative_selectors', [])
        if alt_selectors:
            lines.append(f"  - Fallbacks: {', '.join(f'`{s}`' for s in alt_selectors[:2])}")
        
        lines.append("")
    
    return "\n".join(lines)


def _format_test_steps(test_steps: list) -> str:
    """Format test_steps list for prompt."""
    if not test_steps:
        return "(No test steps provided - generate based on feature type and UI components)"
    
    lines = []
    for step_data in test_steps:
        step_num = step_data.get('step', 0)
        action = step_data.get('action', '')
        component = step_data.get('component', '')
        description = step_data.get('description', '')
        
        lines.append(f"{step_num}. **{action}** on `{component}`")
        if description:
            lines.append(f"   → {description}")
    
    return "\n".join(lines)


def _extract_test_code(response: str) -> str:
    """Extract TypeScript test code from LLM response."""
    
    patterns = [
        r'```(?:typescript|ts)\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            code = match.group(1).strip()
            if "import {" in code and "test" in code:
                return code
    
    if "import {" in response and "test(" in response:
        return response.strip()
    
    return ""


def _generate_fallback_test(feature: dict) -> str:
    """Generate a basic fallback test if AI fails."""
    
    feature_name = feature.get('name', 'Feature Test')
    entry_point = feature.get('entry_point', '/')
    feature_type = feature.get('type', 'unknown')
    description = feature.get('description', 'No description available')
    ui_components = feature.get('ui_components', {})
    test_steps = feature.get('test_steps', [])
    
    feature_name_safe = feature_name.replace("'", "\\'")
    description_safe = description.replace("'", "\\'")
    
    # Build test steps from metadata
    test_actions = []
    
    if test_steps and ui_components:
        test_actions.append("    // Execute test steps from metadata\n")
        
        for step_data in test_steps:
            step_num = step_data.get('step', 0)
            action = step_data.get('action', 'click')
            component_name = step_data.get('component', '')
            step_desc = step_data.get('description', '')
            
            if component_name in ui_components:
                component = ui_components[component_name]
                selector = component.get('selector', '')
                
                test_actions.append(f"    // Step {step_num}: {step_desc}\n")
                
                if action == "fill":
                    test_value = component.get('test_value', 'Test data')
                    test_actions.append(f"    await page.fill('{selector}', '{test_value}');\n")
                    test_actions.append(f"    await expect(page.locator('{selector}')).toHaveValue('{test_value}');\n")
                elif action == "click":
                    test_actions.append(f"    await page.click('{selector}');\n")
                    test_actions.append(f"    await page.waitForLoadState('networkidle');\n")
                elif action == "select":
                    test_actions.append(f"    await page.selectOption('{selector}', '{{value}}');\n")
                
                test_actions.append("\n")
    
    test_actions_code = "".join(test_actions) if test_actions else "    // TODO: Add specific test actions\n"
    
    return f"""import {{ test, expect }} from '@playwright/test';

test.describe('{feature_name_safe}', () => {{
  test.beforeEach(async ({{ page }}) => {{
    test.setTimeout(60000);
    
    await page.goto('{entry_point}');
    await page.waitForLoadState('networkidle');
  }});

  test('should test {feature_name_safe} functionality', async ({{ page }}) => {{
    // Feature: {description_safe}
    // Type: {feature_type}
    
    await expect(page).toHaveURL(new RegExp('{entry_point.replace("/", "\\/")}'));
    
{test_actions_code}
    await page.screenshot({{ path: 'test-results/{feature.get("id", "test")}-result.png', fullPage: true }});
    
    console.log('Test executed for: {feature_name_safe}');
  }});
}});
"""
