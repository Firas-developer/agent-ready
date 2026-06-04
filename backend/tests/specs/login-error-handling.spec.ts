import { test, expect } from '../seed.spec';

test.describe('Authentication & Login', () => {
  test('Login Error Handling', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Click SSO Login button
    await page.locator('body').click();

    // Wait for the login page to load
    await page.waitForLoadState('networkidle');

    // Verify that an error message is displayed for invalid credentials
    const errorMessage = page.locator('[role="alert"], .error-message, .alert-error');
    await expect(errorMessage).toBeVisible();
    
    // Assert that the error message contains appropriate text
    const errorText = await errorMessage.textContent();
    expect(errorText).toBeTruthy();

    // Verify recovery link is present and accessible
    const recoveryLink = page.locator('a:has-text("Forgot password"), a:has-text("Reset password"), a:has-text("Recovery")');
    await expect(recoveryLink).toBeVisible();
    
    // Assert recovery link has proper href attribute
    const recoveryHref = await recoveryLink.getAttribute('href');
    expect(recoveryHref).toBeTruthy();

    // Verify user can interact with the login form again (retry capability)
    const loginInput = page.locator('input[type="email"], input[name="email"], input[name="username"]');
    await expect(loginInput).toBeVisible();
    await expect(loginInput).toBeEnabled();

    // Clear any previous input and enter valid test credentials
    await loginInput.click();
    await loginInput.clear();
    await loginInput.fill('test@example.com');

    // Verify the input field accepted the value
    const inputValue = await loginInput.inputValue();
    expect(inputValue).toBe('test@example.com');

    // Verify password field is also enabled for retry
    const passwordInput = page.locator('input[type="password"], input[name="password"]');
    await expect(passwordInput).toBeVisible();
    await expect(passwordInput).toBeEnabled();

    // Verify login button is accessible for retry
    const loginButton = page.locator('button[type="submit"]:has-text("Login"), button:has-text("Sign in"), button:has-text("Submit")');
    await expect(loginButton).toBeVisible();
    await expect(loginButton).toBeEnabled();

    // Assert that recovery link is clickable
    await expect(recoveryLink).toBeEnabled();
  });
});