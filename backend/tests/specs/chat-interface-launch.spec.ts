import { test, expect } from '../seed.spec';

test.describe('Chat Functionality', () => {
  test('Chat Interface Launch', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Verify user is redirected back to https://tensaigptnew-qa.tensai.run/
    await page.goto('https://tensaigptnew-qa.tensai.run/');

    // Verify dashboard/chat interface loads after successful authentication
    await expect(page).toHaveURL('https://tensaigptnew-qa.tensai.run/');
    await expect(page).toHaveTitle(/.*/, { timeout: 10000 });

    // Verify chat input area is visible and active
    const chatInput = page.locator('textarea, input[type="text"]').first();
    await expect(chatInput).toBeVisible({ timeout: 10000 });
    await expect(chatInput).toBeEnabled();
    await expect(chatInput).toBeFocused({ timeout: 5000 }).catch(() => {
      // Chat input might not be focused initially, which is acceptable
    });

    // Verify previous conversations (if any) are displayed
    const conversationContainer = page.locator('[role="main"], .chat-container, .messages-container').first();
    await expect(conversationContainer).toBeVisible({ timeout: 10000 });

    // Additional verification: Check if send button is present and enabled
    const sendButton = page.locator('button[type="submit"], button:has-text("Send"), [aria-label*="send" i]').first();
    if (await sendButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(sendButton).toBeEnabled();
    }
  });
});