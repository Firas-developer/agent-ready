import { test, expect } from '../seed.spec';

test.describe('Chat Functionality', () => {
  test('Chat Interface Availability', async ({ authenticatedPage }) => {
    // Navigate to the chat interface
    await authenticatedPage.goto('/chat');

    // Wait for the chat interface to load
    await authenticatedPage.waitForLoadState('networkidle');

    // Verify chat container is visible
    const chatContainer = authenticatedPage.locator('[data-testid="chat-container"]');
    await expect(chatContainer).toBeVisible();

    // Verify conversation area is present and visible
    const conversationArea = authenticatedPage.locator('[data-testid="conversation-area"]');
    await expect(conversationArea).toBeVisible();

    // Verify chat input field is present and visible
    const inputField = authenticatedPage.locator('[data-testid="chat-input-field"]');
    await expect(inputField).toBeVisible();

    // Verify input field is enabled and ready for interaction
    await expect(inputField).toBeEnabled();

    // Verify input field is focused or can be focused
    await inputField.focus();
    await expect(inputField).toBeFocused();

    // Verify chat send button is present and visible
    const sendButton = authenticatedPage.locator('[data-testid="chat-send-button"]');
    await expect(sendButton).toBeVisible();

    // Verify send button is enabled
    await expect(sendButton).toBeEnabled();

    // Verify conversation area is empty initially
    const messageList = authenticatedPage.locator('[data-testid="message-list"]');
    const messageCount = await messageList.locator('[data-testid="message-item"]').count();
    await expect(messageCount).toBe(0);

    // Verify chat interface is fully loaded by checking for any loading indicators
    const loadingIndicator = authenticatedPage.locator('[data-testid="chat-loading"]');
    await expect(loadingIndicator).not.toBeVisible();
  });
});