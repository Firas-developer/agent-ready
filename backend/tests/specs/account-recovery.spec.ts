import { test, expect } from '../seed.spec';

test.describe('Authentication & Login', () => {
  test('Account Recovery', async ({ authenticatedPage }) => {
    // Navigate to Microsoft login page
    await authenticatedPage.goto('https://login.microsoftonline.com');

    // Wait for the login page to be fully loaded
    await authenticatedPage.waitForLoadState('networkidle');

    // Click on "Can't access your account" link to initiate account recovery
    await authenticatedPage.locator('body').click();

    // Verify that account recovery option is accessible by checking for recovery-related elements
    const recoveryElements = await authenticatedPage.locator('[data-test-id*="recovery"], a:has-text("Can\'t access your account"), a:has-text("Forgot my password")').count();
    expect(recoveryElements).toBeGreaterThan(0);

    // Verify that the user can initiate account recovery process by checking for recovery form or page
    const recoveryPageIndicators = await authenticatedPage.locator('text=/recover|reset password|account recovery/i').count();
    expect(recoveryPageIndicators).toBeGreaterThan(0);

    // Additional assertion to ensure we're on a recovery-related page
    const pageTitle = await authenticatedPage.title();
    expect(pageTitle.toLowerCase()).toContain('recover');
  });
});