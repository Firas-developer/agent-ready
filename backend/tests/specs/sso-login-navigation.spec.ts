import { test, expect } from '../seed.spec';

test.describe('Authentication & Landing Page', () => {
  test('SSO Login Navigation', async ({ authenticatedPage }) => {
    // Navigate to the application
    await authenticatedPage.goto('/');

    // Wait for the page to load and check for SSO login button
    await authenticatedPage.waitForLoadState('networkidle');

    // Click on SSO login or Microsoft Entra ID login option
    const ssoLoginButton = authenticatedPage.locator('button:has-text("Sign in with Microsoft")');
    await ssoLoginButton.click();

    // Wait for redirect to Microsoft Entra ID login page
    await authenticatedPage.waitForURL(/.*login\.microsoftonline\.com.*/, { timeout: 10000 });

    // Verify redirected to Microsoft Entra ID login
    const currentUrl = authenticatedPage.url();
    expect(currentUrl).toContain('login.microsoftonline.com');

    // Verify sign-in form displays with email/phone/Skype input field
    const emailInput = authenticatedPage.locator('input[type="email"], input[name="loginfmt"], input[placeholder*="email" i], input[placeholder*="phone" i]');
    await expect(emailInput).toBeVisible();

    // Verify 'Next' button is available
    const nextButton = authenticatedPage.locator('button:has-text("Next"), button:has-text("Sign in"), button[type="submit"]');
    await expect(nextButton).toBeVisible();
    await expect(nextButton).toBeEnabled();

    // Verify sign-in options button is visible
    const signInOptionsButton = authenticatedPage.locator('button:has-text("Sign-in options"), button:has-text("More options"), button[title*="options" i]');
    await expect(signInOptionsButton).toBeVisible();

    // Verify footer links are present (Terms of use, Privacy & cookies)
    const termsLink = authenticatedPage.locator('a:has-text("Terms of use"), a[href*="terms"], a[aria-label*="terms" i]');
    await expect(termsLink).toBeVisible();

    const privacyLink = authenticatedPage.locator('a:has-text("Privacy & cookies"), a:has-text("Privacy"), a[href*="privacy"]');
    await expect(privacyLink).toBeVisible();
  });
});