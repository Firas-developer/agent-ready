import { test, expect } from '../seed.spec';

test.describe('Authentication & Landing Page', () => {
  test('Initial Page Load', async ({ authenticatedPage }) => {
    // Navigate to the application URL
    await authenticatedPage.goto('https://tensaigptnew-qa.tensai.run/');

    // Verify page title shows 'Tensai-GPT'
    await expect(authenticatedPage).toHaveTitle(/Tensai-GPT/);

    // Verify welcome heading displays 'tensaiGPT'
    const welcomeHeading = authenticatedPage.locator('h1, h2, [role="heading"]', {
      hasText: /tensaiGPT/i,
    });
    await expect(welcomeHeading).toBeVisible();
    await expect(welcomeHeading).toContainText('tensaiGPT');

    // Verify tagline 'SMARTER CHATS BRIGHTER IDEAS' is visible
    const tagline = authenticatedPage.locator('text=/SMARTER CHATS BRIGHTER IDEAS/i');
    await expect(tagline).toBeVisible();

    // Verify 'SSO Login' button is present and clickable
    const ssoLoginButton = authenticatedPage.locator('button, a', {
      hasText: /SSO Login/i,
    });
    await expect(ssoLoginButton).toBeVisible();
    await expect(ssoLoginButton).toBeEnabled();
  });
});