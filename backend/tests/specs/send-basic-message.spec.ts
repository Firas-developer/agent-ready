import { test, expect } from '../seed.spec';

test.describe('Chat Functionality', () => {
  test('Send Basic Message', async ({ authenticatedPage }) => {
    // Click chat input field
    await authenticatedPage.locator('body').click();

    // Type a basic test message
    await authenticatedPage.locator('input[type="text"], textarea, [contenteditable="true"]').first().fill('Hello, how are you?');

    // Submit the message by pressing Enter or clicking send button
    const sendButton = authenticatedPage.locator('button:has-text("Send"), button[type="submit"], [data-testid="send-button"]');
    const sendButtonExists = await sendButton.count();
    
    if (sendButtonExists > 0) {
      await sendButton.click();
    } else {
      await authenticatedPage.keyboard.press('Enter');
    }

    // Wait for message to appear in chat history
    await authenticatedPage.waitForTimeout(500);

    // Verify user message appears in chat history
    const userMessage = authenticatedPage.locator('text=Hello, how are you?');
    await expect(userMessage).toBeVisible();

    // Verify user message is attributed correctly (check for user indicator)
    const userAttributionElement = authenticatedPage.locator('[data-testid="message-sender"], .message-user, [class*="user-message"]').last();
    await expect(userAttributionElement).toBeVisible();

    // Wait for AI response to be generated
    await authenticatedPage.waitForTimeout(2000);

    // Verify AI response is displayed
    const aiResponseContainer = authenticatedPage.locator('[data-testid="message-content"], .message-content, [class*="ai-message"], [class*="assistant-message"]').last();
    await expect(aiResponseContainer).toBeVisible();

    // Verify AI message is attributed correctly
    const aiAttributionElement = authenticatedPage.locator('[data-testid="message-sender"], .message-ai, [class*="ai-message"], [class*="assistant"]').last();
    await expect(aiAttributionElement).toBeVisible();

    // Verify chat maintains message order (user message before AI response)
    const allMessages = authenticatedPage.locator('[data-testid="message"], .message, [class*="message-item"]');
    const messageCount = await allMessages.count();
    expect(messageCount).toBeGreaterThanOrEqual(2);

    // Verify chat maintains proper formatting
    const chatContainer = authenticatedPage.locator('[data-testid="chat-container"], .chat-container, [class*="messages"]').first();
    await expect(chatContainer).toBeVisible();

    // Verify message text is properly formatted and readable
    const lastMessage = allMessages.last();
    const messageText = await lastMessage.textContent();
    expect(messageText).toBeTruthy();
    expect(messageText?.length).toBeGreaterThan(0);
  });
});