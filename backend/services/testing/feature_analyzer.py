"""
Feature Analyzer - AI-powered feature detection from source code
IMPROVED with better debugging and fallback extraction
"""
import json
import json5
import re
import uuid
import asyncio
from pathlib import Path
from typing import AsyncGenerator, List, Dict


async def analyze_and_detect_features(
    project_path: str,
    provider: str = "azure_foundry_claude",
    model: str = None
) -> AsyncGenerator[str, None]:
    """
    Analyze project and detect testable features.
    
    Yields:
        SSE progress messages and detected features
    """
    yield "data: 📖 Reading project files...\n\n"
    
    # Read source files
    file_contents, files_read = _read_source_files(project_path, max_files=30)
    
    yield f"data: ✅ Read {len(files_read)} source files\n\n"
    
    for i, filename in enumerate(files_read[:10], 1):
        yield f"data:    {i}. {filename}\n\n"
    
    if len(files_read) > 10:
        yield f"data:    ... and {len(files_read) - 10} more\n\n"
    
    yield "data: \n\n"
    yield "data: 🤖 Analyzing with AI to detect features...\n\n"
    
    # Detect features with AI
    try:
        features, ai_response = await _ai_detect_features(
            file_contents, files_read, provider, model
        )
        
        if features:
            yield f"data: ✅ Detected {len(features)} features:\n\n"
            for i, feat in enumerate(features, 1):
                yield f"data:    {i}. {feat['name']} ({feat.get('type', 'unknown')})\n\n"
        else:
            yield "data: ⚠️ AI detection failed, using filename-based detection\n\n"
            
            # Show debug info
            if ai_response:
                yield f"data: 🔍 AI Response Preview: {ai_response[:200]}...\n\n"
            
            # Use filename-based fallback
            features = _extract_features_from_filenames(files_read)
            
            yield f"data: ✅ Extracted {len(features)} features from filenames:\n\n"
            for i, feat in enumerate(features, 1):
                yield f"data:    {i}. {feat['name']}\n\n"
        
        yield "data: \n\n"
        yield "data: __FEATURES_JSON__\n\n"
        yield f"data: {json.dumps(features, indent=2)}\n\n"
        
    except Exception as e:
        yield f"data: ❌ Detection error: {e}\n\n"
        
        # Use filename-based fallback
        features = _extract_features_from_filenames(files_read)
        
        yield f"data: 🔄 Using filename-based fallback: {len(features)} features\n\n"
        yield "data: __FEATURES_JSON__\n\n"
        yield f"data: {json.dumps(features, indent=2)}\n\n"


def _read_source_files(project_path: str, max_files: int = 30) -> tuple:
    """Read source files for analysis."""
    root = Path(project_path)
    contents = []
    files_read = []
    
    # Prioritize important files
    patterns = [
        "**/Login*.tsx", "**/Login*.jsx", "**/login*.jsx",
        "**/Auth*.tsx", "**/Auth*.jsx",
        "**/Chat*.tsx", "**/Chat*.jsx", "**/chat*.jsx",
        "**/Dashboard*.tsx", "**/Dashboard*.jsx",
        "**/routes/*.py", "**/routers/*.py",
        "**/pages/**/*.tsx", "**/components/**/*.tsx",
        "**/pages/**/*.jsx", "**/components/**/*.jsx",
    ]
    
    seen = set()
    
    for pattern in patterns:
        if len(files_read) >= max_files:
            break
        
        for file in root.glob(pattern):
            if 'node_modules' in file.parts or '.venv' in file.parts:
                continue
            
            if file in seen:
                continue
            
            seen.add(file)
            
            try:
                rel_path = str(file.relative_to(root)).replace('\\', '/')
                content = file.read_text(encoding='utf-8', errors='ignore')
                
                if len(content.strip()) < 50:
                    continue
                
                # Limit file size
                if len(content) > 3000:
                    content = content[:3000] + "\n... (truncated)"
                
                contents.append(f"\n## File: {rel_path}\n```\n{content}\n```\n")
                files_read.append(rel_path)
                
            except:
                pass
    
    return "\n".join(contents), files_read


async def _ai_detect_features(
    file_contents: str,
    files_read: List[str],
    provider: str,
    model: str = None
) -> tuple:
    """Use AI to detect features. Returns (features, ai_response)."""
    
    from llm.client import LLMClient
    
    system_prompt = """You are a QA automation expert analyzing a codebase.

Extract ALL testable features and return ONLY a JSON array. No markdown, no explanations.

Each feature must have:
{
  "name": "Feature Name",
  "type": "authentication|navigation|interaction|form",
  "priority": "high|medium|low",
  "entry_point": "/path",
  "description": "What it does",
  "ui_components": {"button": "selector"},
  "test_steps": [{"step": 1, "action": "click", "component": "button", "description": "Click button"}]
}

Return ONLY the JSON array starting with [ and ending with ]."""
    
    user_prompt = f"""Analyze this codebase and extract testable features.

Files: {', '.join(files_read[:10])}

Code:
{file_contents[:6000]}

Return JSON array of features."""
    
    try:
        client = LLMClient(provider=provider, model=model)
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.complete(system_prompt, user_prompt, max_tokens=4096)
        )
        
        # Extract JSON - Try multiple methods
        features = None
        
        # Method 1: Look for JSON array
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            # Clean
            json_str = re.sub(r'//[^\n]*', '', json_str)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
            try:
                features = json5.loads(json_str)
            except:
                try:
                    features = json.loads(json_str)
                except:
                    pass
        
        # Method 2: Code block
        if not features:
            match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    features = json5.loads(json_str)
                except:
                    try:
                        features = json.loads(json_str)
                    except:
                        pass
        
        # Validate and add IDs
        if features and isinstance(features, list):
            for feature in features:
                if isinstance(feature, dict):
                    if "id" not in feature:
                        feature["id"] = f"feat-{uuid.uuid4().hex[:8]}"
                    feature["detected_from"] = files_read[:3]
            return features, response
        
        return [], response
        
    except Exception as e:
        print(f"AI detection error: {e}")
        return [], str(e)


def _extract_features_from_filenames(files_read: List[str]) -> List[Dict]:
    """Extract features based on filenames when AI fails."""
    features = []
    
    # Pattern matching
    patterns = {
        "login": {"name": "User Authentication", "type": "authentication", "entry_point": "/login"},
        "auth": {"name": "Authentication Flow", "type": "authentication", "entry_point": "/"},
        "chat": {"name": "Chat Interface", "type": "interaction", "entry_point": "/chat"},
        "dashboard": {"name": "Dashboard", "type": "navigation", "entry_point": "/dashboard"},
        "profile": {"name": "User Profile", "type": "form", "entry_point": "/profile"},
        "settings": {"name": "Settings", "type": "form", "entry_point": "/settings"},
    }
    
    seen_types = set()
    
    for file in files_read:
        file_lower = file.lower()
        
        for keyword, feature_data in patterns.items():
            if keyword in file_lower and feature_data["type"] not in seen_types:
                features.append({
                    "id": f"feat-{uuid.uuid4().hex[:8]}",
                    "name": feature_data["name"],
                    "type": feature_data["type"],
                    "priority": "high",
                    "entry_point": feature_data["entry_point"],
                    "description": f"Detected from {file}",
                    "detected_from": [file],
                    "ui_components": {},
                    "test_steps": [
                        {"step": 1, "action": "navigate", "component": "page", "description": f"Navigate to {feature_data['entry_point']}"}
                    ]
                })
                seen_types.add(feature_data["type"])
    
    # Always add at least navigation
    if not features:
        features.append({
            "id": "feat-fallback",
            "name": "Application Navigation",
            "type": "navigation",
            "priority": "high",
            "entry_point": "/",
            "description": "Basic navigation test",
            "ui_components": {},
            "test_steps": [
                {"step": 1, "action": "navigate", "component": "page", "description": "Navigate to /"}
            ]
        })
    
    return features
