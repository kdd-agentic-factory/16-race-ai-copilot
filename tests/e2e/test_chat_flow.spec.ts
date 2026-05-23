import { test, expect } from '@playwright/test';

/**
 * Shared mock response that simulates a successful backend reply.
 * Used across tests so the frontend gets a consistent structured answer.
 */
const MOCK_CHAT_RESPONSE = {
  conversation_id: 'conv_test',
  message_id: 'msg_test',
  answer:
    'Based on the evidence from telemetry data, tire degradation increases after lap 10. ' +
    'I recommend adjusting the rear camber by -0.3 degrees to compensate.',
  confidence: 0.85,
  evidence: [
    {
      id: 'ev_1',
      title: 'Telemetry Report',
      snippet: 'Tire degradation increases after lap 10 with current setup.',
    },
    {
      id: 'ev_2',
      title: 'Historical Setup Database',
      snippet: 'Previous runs at this circuit used -2.1° rear camber for consistent wear.',
    },
  ],
  tool_calls: [
    {
      tool_name: 'telemetry.query_features',
      parameters: { feature: 'tire_wear', lap_range: [5, 15] },
      result: {},
    },
  ],
  recommendations: [
    {
      action: 'Reduce rear camber by 0.3°',
      rationale: 'Improves tire longevity in high-temperature conditions.',
    },
  ],
  approval_required: false,
  approver_role: null,
  uncertainty: null,
  next_actions: ['Review evidence', 'Apply setup change'],
};

/**
 * Helper: register a route on the page that intercepts POST /api/chat
 * and returns a given body as a JSON 200 response.
 */
async function mockChatApi(
  page: import('@playwright/test').Page,
  body: Record<string, unknown> = MOCK_CHAT_RESPONSE,
) {
  await page.route('**/api/chat', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
}

test.describe('Chat flow', () => {
  test.beforeEach(async ({ page }) => {
    await mockChatApi(page);
    await page.goto('/');
  });

  test('Page loads and shows the correct title and empty state', async ({ page }) => {
    // Document <title>
    await expect(page).toHaveTitle(/Race AI Copilot/);

    // The empty-state heading
    await expect(
      page.getByRole('heading', { name: 'Race AI Copilot' }),
    ).toBeVisible();

    // Sidebar brand heading (desktop)
    const sidebarBrand = page.locator('aside h1');
    await expect(sidebarBrand).toHaveText('Race Copilot');
  });

  test('Chat input has the correct placeholder', async ({ page }) => {
    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    await expect(textarea).toBeVisible();
    await expect(textarea).toBeEnabled();
  });

  test('User can type a message in the textarea', async ({ page }) => {
    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    await textarea.fill('What is the tire degradation trend?');
    await expect(textarea).toHaveValue('What is the tire degradation trend?');
  });

  test('User can click the send button and user bubble appears', async ({ page }) => {
    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    const sendButton = page.getByRole('button', { name: 'Send message' });

    await textarea.fill('Suggest a setup for understeer in T4');
    await sendButton.click();

    // User bubble appears with the sent text
    const userBubble = page.locator('.max-w-\\[80%\\]').first();
    await expect(userBubble).toBeVisible();
    await expect(userBubble).toContainText('Suggest a setup for understeer in T4');

    // The bubble should have "You" header
    await expect(userBubble).toContainText('You');
  });

  test('Assistant response appears after sending a message', async ({ page }) => {
    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    const sendButton = page.getByRole('button', { name: 'Send message' });

    await textarea.fill('What is the tire degradation trend?');
    await sendButton.click();

    // After the mock resolves, the assistant answer should be visible
    const assistantText = MOCK_CHAT_RESPONSE.answer;
    await expect(page.getByText(assistantText)).toBeVisible({ timeout: 10000 });

    // Assistant message should show confidence percentage
    await expect(page.getByText('85% confidence')).toBeVisible();

    // Next actions link should appear
    await expect(page.getByText('Next actions')).toBeVisible();
  });

  test('Evidence sources are linked in the assistant response', async ({ page }) => {
    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    const sendButton = page.getByRole('button', { name: 'Send message' });

    await textarea.fill('What is the tire degradation trend?');
    await sendButton.click();

    // Wait for assistant answer
    await expect(
      page.getByText(MOCK_CHAT_RESPONSE.answer),
    ).toBeVisible({ timeout: 10000 });

    // Evidence source button should appear
    const evidenceButton = page.getByText('2 evidence sources');
    await expect(evidenceButton).toBeVisible();
  });

  test('Clicking a suggestion button sends that message', async ({ page }) => {
    // Suggestion buttons are only visible in the empty state (no messages yet)
    const suggestionText = 'Best brake duct for Monaco';
    const suggestionButton = page.getByRole('button', { name: suggestionText });

    await expect(suggestionButton).toBeVisible();
    await suggestionButton.click();

    // After clicking, the user bubble should appear with the suggestion text
    const userBubble = page.locator('.max-w-\\[80%\\]').first();
    await expect(userBubble).toBeVisible();
    await expect(userBubble).toContainText(suggestionText);
  });

  test('Clicking all suggestion buttons work in sequence', async ({ page }) => {
    const suggestions = [
      'What is the tire degradation trend?',
      'Suggest a setup for understeer in T4',
      'Best brake duct for Monaco',
      'Simulate lap 5 with current fuel',
    ];

    for (const suggestion of suggestions) {
      const btn = page.getByRole('button', { name: suggestion });
      await expect(btn).toBeVisible();
      await btn.click();

      // The user bubble should show the suggestion text
      const userBubble = page.locator('.max-w-\\[80%\\]').first();
      await expect(userBubble).toContainText(suggestion);

      // Wait for the assistant answer to appear, then clear for next iteration
      await expect(
        page.getByText(MOCK_CHAT_RESPONSE.answer),
      ).toBeVisible({ timeout: 10000 });

      // Clear conversation to reset to empty state for the next suggestion
      await page.getByText('Clear conversation').click();
    }
  });
});
