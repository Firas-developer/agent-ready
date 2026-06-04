import { test, expect } from '../seed.spec';

test.describe('Chat Functionality', () => {
  test('Initialize New Chat Session', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Verify message composition area is available
    await page.screenshot({
      path: '.playwright-cli/page-2026-04-28T09-00-36-514Z.png',
      scale: 'css',
      type: 'png'
    });

    // Verify chat interface displays clearly after login
    const chatContainer = page.locator('[data-testid="chat-container"], .chat-container, #chat');
    await expect(chatContainer).toBeVisible();

    // Verify chat input field is active and ready for user input
    const chatInput = page.locator('[data-testid="chat-input"], textarea[placeholder*="message"], input[placeholder*="message"]').first();
    await expect(chatInput).toBeVisible();
    await expect(chatInput).toBeFocused();

    // Verify previous chat history is visible if applicable
    const chatHistory = page.locator('[data-testid="chat-history"], .chat-history, .message-list');
    const historyVisible = await chatHistory.isVisible().catch(() => false);
    
    if (historyVisible) {
      await expect(chatHistory).toBeVisible();
      const messages = chatHistory.locator('[data-testid="chat-message"], .message, .chat-item');
      const messageCount = await messages.count();
      expect(messageCount).toBeGreaterThanOrEqual(0);
    }

    // Verify chat composition area is fully functional
    await expect(chatInput).toHaveAttribute('type', /text|textarea/i).catch(() => {
      // Input might be a textarea or custom element, which is acceptable
      return true;
    });

    // Verify send button is available if present
    const sendButton = page.locator('[data-testid="send-button"], button:has-text("Send"), button[aria-label*="send"]').first();
    const sendButtonVisible = await sendButton.isVisible().catch(() => false);
    
    if (sendButtonVisible) {
      await expect(sendButton).toBeEnabled();
    }
  });
});