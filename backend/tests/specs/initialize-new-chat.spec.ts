import { test, expect } from '../seed.spec';

test.describe('Chat Functionality', () => {
  test('Initialize New Chat', async ({ authenticatedPage }) => {
    const page = authenticatedPage;

    // Click on chat input field to focus it
    await page.locator('body').click();

    // Verify chat input field is accessible and focused
    const chatInputField = page.locator('input[type="text"], textarea');
    await expect(chatInputField).toBeFocused();

    // Verify cursor appears in input field by checking focus state
    const isFocused = await chatInputField.evaluate((el: HTMLElement) => {
      return document.activeElement === el;
    });
    expect(isFocused).toBeTruthy();

    // Verify chat interface is fully loaded
    const chatContainer = page.locator('[role="main"], .chat-container, .chat-interface');
    await expect(chatContainer).toBeVisible();

    // Verify input field is visible and enabled
    await expect(chatInputField).toBeVisible();
    await expect(chatInputField).toBeEnabled();
  });
});