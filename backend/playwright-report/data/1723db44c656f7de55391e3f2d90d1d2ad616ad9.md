# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: initialize-new-chat.spec.ts >> Chat Functionality >> Initialize New Chat
- Location: tests\specs\initialize-new-chat.spec.ts:4:7

# Error details

```
Error: locator.click: Target page, context or browser has been closed
Call log:
  - waiting for getByRole('button', { name: 'SSO Login' })

```

```
Error: apiRequestContext._wrapApiCall: Target page, context or browser has been closed
```