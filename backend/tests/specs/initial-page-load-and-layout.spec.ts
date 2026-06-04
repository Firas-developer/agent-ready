import { test, expect } from '../seed.spec';

test.describe('Authentication & Landing Page', () => {
  test('Initial Page Load and Layout', async ({ authenticatedPage }) => {
    // Navigate to the application URL
    await authenticatedPage.goto('https://tensaigptnew-qa.tensai.run/');

    // Wait for the page to load completely
    await authenticatedPage.waitForLoadState('networkidle');

    // Verify page title displays 'Tensai-GPT'
    const pageTitle = await authenticatedPage.title();
    expect(pageTitle).toContain('Tensai-GPT');

    // Verify welcome message displays 'Welcome to tensaiGPT'
    const welcomeMessage = authenticatedPage.locator('text=Welcome to tensaiGPT');
    await expect(welcomeMessage).toBeVisible();

    // Verify tagline 'SMARTER CHATS BRIGHTER IDEAS' is visible
    const tagline = authenticatedPage.locator('text=SMARTER CHATS BRIGHTER IDEAS');
    await expect(tagline).toBeVisible();

    // Verify SSO Login button is present and interactive
    const ssoLoginButton = authenticatedPage.locator('button:has-text("SSO Login"), a:has-text("SSO Login"), [role="button"]:has-text("SSO Login")');
    await expect(ssoLoginButton).toBeVisible();
    await expect(ssoLoginButton).toBeEnabled();

    // Verify the button is clickable by checking hover state is possible
    await ssoLoginButton.hover();
    await expect(ssoLoginButton).toHaveClass(/.*interactive|.*button|.*clickable.*/i);
  });
});