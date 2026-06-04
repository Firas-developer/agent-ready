import { test, expect } from '../seed.spec';

test.describe('Authentication & Login', () => {
  test('Sign-in Options Availability', async ({ authenticatedPage }) => {
    // Select available sign-in method
    await authenticatedPage.locator('body').click();

    // Verify multiple sign-in options are accessible
    const signInOptionsContainer = authenticatedPage.locator('[data-testid="sign-in-options"], .sign-in-options, [role="tablist"]').first();
    await expect(signInOptionsContainer).toBeVisible();

    // Verify user can choose alternative authentication method
    const alternativeSignInMethods = authenticatedPage.locator('button[data-testid*="signin"], a[data-testid*="signin"], button:has-text("Sign in"), a:has-text("Sign in")');
    const methodCount = await alternativeSignInMethods.count();
    expect(methodCount).toBeGreaterThanOrEqual(1);

    // Verify at least one sign-in option is clickable
    const firstSignInOption = authenticatedPage.locator('button[data-testid*="signin"], a[data-testid*="signin"]').first();
    await expect(firstSignInOption).toBeEnabled();
  });
});