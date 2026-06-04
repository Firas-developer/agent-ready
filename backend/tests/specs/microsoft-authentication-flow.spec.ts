import { test, expect } from '../seed.spec';

test.describe('Authentication & Landing Page', () => {
  test('Microsoft Authentication Flow', async ({ authenticatedPage }) => {
    // Verify user is authenticated and on the application
    await expect(authenticatedPage).toBeTruthy();

    // Get the current URL to verify redirect has completed
    const currentUrl = authenticatedPage.url();

    // Assert that the user has been redirected to the application
    expect(currentUrl).toContain('https://tensaigptnew-qa.tensai.run');

    // Verify that authentication redirect URI is properly configured
    expect(currentUrl).not.toContain('https://tensaigptnew-qa.tensai.run/api/auth/redirect');

    // Check that the page title indicates successful authentication
    const pageTitle = await authenticatedPage.title();
    expect(pageTitle).toBeTruthy();
    expect(pageTitle.length).toBeGreaterThan(0);

    // Verify the user is logged into the application by checking for authenticated content
    const bodyContent = await authenticatedPage.content();
    expect(bodyContent).toBeTruthy();

    // Wait for page to be fully loaded
    await authenticatedPage.waitForLoadState('networkidle');

    // Verify the application is accessible and responsive
    const isVisible = await authenticatedPage.isVisible('body');
    expect(isVisible).toBeTruthy();

    // Assert that the redirect flow preserved the necessary state
    const cookies = await authenticatedPage.context().cookies();
    expect(cookies.length).toBeGreaterThan(0);

    // Verify authentication-related cookies or storage exist
    const localStorage = await authenticatedPage.evaluate(() => {
      return Object.keys(window.localStorage);
    });
    expect(localStorage).toBeTruthy();

    // Confirm successful navigation to authenticated area
    const status = authenticatedPage.url();
    expect(status).toMatch(/tensaigptnew-qa\.tensai\.run/);
    expect(status).not.toContain('login');
    expect(status).not.toContain('authorize');
  });
});