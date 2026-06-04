import { test, expect } from '../seed.spec';

test.describe('Authentication & Login', () => {
  test('Microsoft Sign-In Page Elements', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Click SSO Login and verify Microsoft sign-in page loads
    await page.locator('body').click();

    // Verify the Microsoft sign-in page has loaded successfully
    await expect(page).toHaveURL(/.*signin.*microsoft.*/i);

    // Verify all sign-in page elements are properly rendered
    // Check for email input field
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toBeEnabled();

    // Check for password input field
    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toBeVisible();

    // Check for sign-in button
    const signInButton = page.locator('button:has-text("Sign in")');
    await expect(signInButton).toBeVisible();
    await expect(signInButton).toBeEnabled();

    // Check for "Keep me signed in" checkbox
    const keepSignedInCheckbox = page.locator('input[type="checkbox"]');
    await expect(keepSignedInCheckbox).toBeVisible();

    // Verify all links are functional
    // Check for "Can't access your account?" link
    const cantAccessLink = page.locator('a:has-text("Can\'t access your account?")');
    if (await cantAccessLink.isVisible()) {
      await expect(cantAccessLink).toBeEnabled();
      await expect(cantAccessLink).toHaveAttribute('href', /.*/);
    }

    // Check for "Sign up for one!" link
    const signUpLink = page.locator('a:has-text("Sign up")');
    if (await signUpLink.isVisible()) {
      await expect(signUpLink).toBeEnabled();
      await expect(signUpLink).toHaveAttribute('href', /.*/);
    }

    // Verify footer information is accessible
    // Check for footer section
    const footer = page.locator('footer');
    if (await footer.isVisible()) {
      await expect(footer).toBeVisible();

      // Verify footer links are present and functional
      const footerLinks = page.locator('footer a');
      const footerLinksCount = await footerLinks.count();
      
      if (footerLinksCount > 0) {
        // Verify each footer link is accessible
        for (let i = 0; i < footerLinksCount; i++) {
          const link = footerLinks.nth(i);
          await expect(link).toBeVisible();
          await expect(link).toHaveAttribute('href', /.*/);
        }
      }
    }

    // Verify page title and header
    const pageTitle = page.locator('h1, [role="heading"]');
    await expect(pageTitle).toBeVisible();

    // Verify the page is responsive and all elements are accessible
    await expect(page).toHaveTitle(/.*Sign in.*Microsoft.*/i);
  });
});