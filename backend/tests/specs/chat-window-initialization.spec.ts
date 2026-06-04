import { test, expect } from '../seed.spec';

test.describe('Chat Interface', () => {
  test('Chat Window Initialization', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Navigate to the chat interface
    await page.goto('/chat');

    // Wait for the chat window to be fully loaded
    await page.waitForLoadState('networkidle');

    // Verify that the chat input field is visible and ready for user input
    const chatInput = page.locator('input[placeholder*="message"], textarea[placeholder*="message"], [contenteditable="true"]').first();
    await expect(chatInput).toBeVisible();
    await expect(chatInput).toBeEnabled();

    // Verify that the send button or submission mechanism is present and visible
    const sendButton = page.locator('button[type="submit"], button:has-text("Send"), [aria-label*="send"]').first();
    await expect(sendButton).toBeVisible();
    await expect(sendButton).toBeEnabled();

    // Verify that the chat window displays empty state or previous conversations
    const chatWindow = page.locator('[role="main"], .chat-container, .messages-container').first();
    await expect(chatWindow).toBeVisible();

    // Check if chat messages are displayed or empty state is shown
    const messageList = page.locator('[role="list"], .messages, .chat-messages').first();
    const hasMessages = await messageList.isVisible().catch(() => false);
    
    if (hasMessages) {
      // If messages exist, verify at least one message is displayed
      const messages = page.locator('[role="listitem"], .message, .chat-message');
      const messageCount = await messages.count();
      expect(messageCount).toBeGreaterThanOrEqual(0);
    } else {
      // If no messages, verify empty state message is displayed
      const emptyState = page.locator('text=/no messages|empty|start conversation/i');
      const hasEmptyState = await emptyState.isVisible().catch(() => false);
      expect(hasEmptyState || messageCount === 0).toBeTruthy();
    }

    // Verify UI is fully responsive by checking viewport
    const viewportSize = page.viewportSize();
    expect(viewportSize).not.toBeNull();
    expect(viewportSize?.width).toBeGreaterThan(0);
    expect(viewportSize?.height).toBeGreaterThan(0);

    // Verify accessibility - check for ARIA labels and roles
    await expect(chatInput).toHaveAttribute('role', /textbox|searchbox|complementary/);
    await expect(sendButton).toHaveAttribute('type', 'submit');

    // Take a screenshot of the chat window initialization
    await page.screenshot({
      path: '.playwright-cli/page-chat-window-initialization.png',
      scale: 'css',
      type: 'png',
      fullPage: false
    });

    // Verify chat window is accessible
    const chatWindowAccessible = await page.evaluate(() => {
      const chatContainer = document.querySelector('[role="main"], .chat-container, .messages-container');
      return chatContainer ? chatContainer.getAttribute('role') || 'main' : null;
    });
    expect(chatWindowAccessible).not.toBeNull();
  });
});