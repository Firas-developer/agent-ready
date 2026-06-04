# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: login-error-handling.spec.ts >> Authentication & Login >> Login Error Handling
- Location: tests\specs\login-error-handling.spec.ts:4:7

# Error details

```
Error: locator.click: Target page, context or browser has been closed
Call log:
  - waiting for getByRole('button', { name: 'SSO Login' })

```

```
Error: apiRequestContext._wrapApiCall: Target page, context or browser has been closed
```