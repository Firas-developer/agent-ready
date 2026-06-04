```markdown
# agent-ready Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill provides guidance for contributing to the `agent-ready` Python codebase. It covers the project's unique coding conventions, including file naming, import/export styles, and commit patterns. While no specific automated workflows are detected, this guide outlines best practices for code structure and testing within the repository.

## Coding Conventions

### File Naming
- Use **camelCase** for Python file names.
  - **Example:**  
    `agentManager.py`  
    `userSessionHandler.py`

### Import Style
- Use **relative imports** within modules.
  - **Example:**
    ```python
    from .utils import parseInput
    from .models import Agent
    ```

### Export Style
- Use **named exports** (explicitly specifying what is exported).
  - **Example:**
    ```python
    __all__ = ['AgentManager', 'UserSessionHandler']
    ```

### Commit Patterns
- Commit messages are freeform, typically concise (average 28 characters).
- No enforced prefix or structure.

## Workflows

### Adding a New Module
**Trigger:** When you need to add new functionality as a module  
**Command:** `/add-module`

1. Create a new Python file using camelCase naming (e.g., `newFeatureModule.py`).
2. Implement your functionality.
3. Use relative imports for any internal dependencies.
4. Add the module's main classes or functions to `__all__` for named exports.
5. Write corresponding tests (see Testing Patterns).

### Updating Imports
**Trigger:** When reorganizing or refactoring code  
**Command:** `/update-imports`

1. Change all import statements to use relative paths within the package.
2. Verify that all imports resolve correctly.
3. Run tests to ensure nothing is broken.

## Testing Patterns

- Tests are written using the **jest** framework (note: this is typically for JavaScript/TypeScript, but the pattern is detected).
- Test files follow the `*.spec.ts` naming convention.
  - **Example:**  
    `agentManager.spec.ts`
- Each test file corresponds to a module and covers its main functionality.

## Commands
| Command         | Purpose                                  |
|-----------------|------------------------------------------|
| /add-module     | Scaffold and add a new Python module     |
| /update-imports | Refactor import statements to be relative|
```
