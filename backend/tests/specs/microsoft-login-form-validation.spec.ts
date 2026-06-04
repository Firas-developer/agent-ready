import { test, expect } from '../seed.spec';

test.describe('Authentication & Login', () => {
  test('Microsoft Login Form Validation', async ({ authenticatedPage }) => {
    // Navigate to the Microsoft login page
    await authenticatedPage.goto('https://login.microsoftonline.com');

    // Wait for the page to fully load
    await authenticatedPage.waitForLoadState('networkidle');

    // Verify email input field is visible and enabled
    const emailInput = authenticatedPage.locator('input[type="email"]');
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toBeEnabled();

    // Verify the "Next" button is present and clickable
    const nextButton = authenticatedPage.locator('button:has-text("Next")');
    await expect(nextButton).toBeVisible();
    await expect(nextButton).toBeEnabled();

    // Verify the Microsoft logo is displayed
    const logo = authenticatedPage.locator('[data-test-id="logo"]');
    await expect(logo).toBeVisible();

    // Verify the "Sign in" heading is present
    const heading = authenticatedPage.locator('h1:has-text("Sign in")');
    await expect(heading).toBeVisible();

    // Verify footer contains Terms of use link
    const termsLink = authenticatedPage.locator('a:has-text("Terms of use")');
    await expect(termsLink).toBeVisible();
    await expect(termsLink).toHaveAttribute('href', /terms/i);

    // Verify footer contains Privacy and cookies link
    const privacyLink = authenticatedPage.locator('a:has-text("Privacy and cookies")');
    await expect(privacyLink).toBeVisible();
    await expect(privacyLink).toHaveAttribute('href', /privacy/i);

    // Verify footer contains Cookie management link
    const cookieLink = authenticatedPage.locator('a:has-text("Cookies")');
    await expect(cookieLink).toBeVisible();

    // Verify the help/troubleshooting button is accessible
    const helpButton = authenticatedPage.locator('button:has-text("Help")');
    await expect(helpButton).toBeVisible();
    await expect(helpButton).toBeEnabled();

    // Verify "Can't access your account?" link is present
    const cantAccessLink = authenticatedPage.locator('a:has-text("Can\'t access your account?")');
    await expect(cantAccessLink).toBeVisible();
    await expect(cantAccessLink).toBeEnabled();

    // Verify all footer links have valid URLs (not empty)
    const footerLinks = authenticatedPage.locator('footer a');
    const linkCount = await footerLinks.count();
    expect(linkCount).toBeGreaterThan(0);

    for (let i = 0; i < linkCount; i++) {
      const href = await footerLinks.nth(i).getAttribute('href');
      expect(href).toBeTruthy();
      expect(href).not.toBe('');
    }

    // Verify that Terms link points to a valid Microsoft domain
    const termsHref = await termsLink.getAttribute('href');
    expect(termsHref).toMatch(/microsoft\.com|microsoft\.info/i);

    // Verify that Privacy link points to a valid Microsoft domain
    const privacyHref = await privacyLink.getAttribute('href');
    expect(privacyHref).toMatch(/microsoft\.com|microsoft\.info/i);

    // Verify help button is keyboard accessible
    await helpButton.focus();
    const isFocused = await helpButton.evaluate((el) => document.activeElement === el);
    expect(isFocused).toBeTruthy();

    // Verify email input accepts text input
    await emailInput.click();
    await emailInput.fill('test@example.com');
    const inputValue = await emailInput.inputValue();
    expect(inputValue).toBe('test@example.com');

    // Verify the page layout is responsive
    const viewport = authenticatedPage.viewportSize();
    expect(viewport).toBeTruthy();
    expect(viewport?.width).toBeGreaterThan(0);
    expect(viewport?.height).toBeGreaterThan(0);
  });
});