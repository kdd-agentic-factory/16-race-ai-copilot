import { test, expect } from '@playwright/test';

/**
 * Mock response where approval_required = true, simulating an action
 * that needs the Crew Chief to sign off before execution.
 */
const APPROVAL_REQUIRED_RESPONSE = {
  conversation_id: 'conv_gov',
  message_id: 'msg_gov_1',
  answer:
    'I recommend changing the front wing angle by -1.5° to reduce understeer ' +
    'in Turn 4. This change requires Crew Chief approval before the telemetry ' +
    'system can apply it to the car setup.',
  confidence: 0.92,
  evidence: [
    {
      id: 'ev_gov_1',
      title: 'Aero Balance Report',
      snippet:
        'Front wing at current angle produces 45N downforce, target is 52N for ' +
        'optimal Turn 4 rotation.',
    },
  ],
  tool_calls: [
    {
      tool_name: 'setup.apply_change',
      parameters: { component: 'front_wing', delta_angle: -1.5 },
      result: {},
    },
  ],
  recommendations: [
    {
      action: 'Deploy front wing -1.5°',
      rationale: 'Shifts aero balance forward, improving turn-in response in T4.',
    },
  ],
  approval_required: true,
  approver_role: 'Crew Chief',
  uncertainty: null,
  next_actions: ['Await approval', 'Review aero data'],
};

/**
 * Standard (non-approval) mock used for the evidence-drawer test
 * so we get a response with evidence we can view.
 */
const STANDARD_RESPONSE = {
  conversation_id: 'conv_std',
  message_id: 'msg_std',
  answer:
    'Based on the telemetry data, suspension damping needs adjustment ' +
    'for the upcoming sector.',
  confidence: 0.78,
  evidence: [
    {
      id: 'ev_std_1',
      title: 'Suspension Telemetry',
      snippet:
        'Front rebound damping is 25% above optimal range causing mid-corner understeer.',
    },
  ],
  tool_calls: [
    {
      tool_name: 'telemetry.query_features',
      parameters: { feature: 'suspension_damping' },
      result: {},
    },
  ],
  recommendations: [],
  approval_required: false,
  approver_role: null,
  uncertainty: null,
  next_actions: ['Review telemetry'],
};

test.describe('Governance & Approval', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('Approval modal appears when response requires Crew Chief approval', async ({
    page,
  }) => {
    // Mock the API to return approval_required: true
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(APPROVAL_REQUIRED_RESPONSE),
      });
    });

    // Send a message about a setup change that triggers governance
    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    const sendButton = page.getByRole('button', { name: 'Send message' });

    await textarea.fill('Suggest a front wing angle change for T4 understeer');
    await sendButton.click();

    // Approval modal should appear
    const modal = page.getByRole('heading', {
      name: 'Crew Chief Approval Required',
    });
    await expect(modal).toBeVisible({ timeout: 10000 });

    const approvalDialog = page.getByRole('dialog', {
      name: 'Crew Chief Approval Required',
    });

    // The proposed tool call should be visible inside the modal
    await expect(approvalDialog.getByText('setup.apply_change')).toBeVisible();

    // The Approve & Execute and Reject buttons should be visible
    await expect(
      page.getByRole('button', { name: 'Approve & Execute' }),
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible();

    // Response preview should show the answer
    await expect(
      approvalDialog.getByText(APPROVAL_REQUIRED_RESPONSE.answer),
    ).toBeVisible();

    // Recommendations should also appear in the modal
    await expect(
      approvalDialog.getByText('Deploy front wing -1.5°'),
    ).toBeVisible();
  });

  test('Reject button closes the approval modal', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(APPROVAL_REQUIRED_RESPONSE),
      });
    });

    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    const sendButton = page.getByRole('button', { name: 'Send message' });

    await textarea.fill('Change setup for T4');
    await sendButton.click();

    await expect(
      page.getByRole('heading', { name: 'Crew Chief Approval Required' }),
    ).toBeVisible({ timeout: 10000 });

    // Click Reject
    await page.getByRole('button', { name: 'Reject' }).click();

    // Modal should close
    await expect(
      page.getByRole('heading', { name: 'Crew Chief Approval Required' }),
    ).not.toBeVisible();
  });

  test('Approve button closes the modal', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(APPROVAL_REQUIRED_RESPONSE),
      });
    });

    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    const sendButton = page.getByRole('button', { name: 'Send message' });

    await textarea.fill('Apply aero change');
    await sendButton.click();

    await expect(
      page.getByRole('heading', { name: 'Crew Chief Approval Required' }),
    ).toBeVisible({ timeout: 10000 });

    // Click Approve & Execute
    await page.getByRole('button', { name: 'Approve & Execute' }).click();

    // Modal should close
    await expect(
      page.getByRole('heading', { name: 'Crew Chief Approval Required' }),
    ).not.toBeVisible();
  });

  test('Evidence drawer can be opened from assistant response', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(STANDARD_RESPONSE),
      });
    });

    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    const sendButton = page.getByRole('button', { name: 'Send message' });

    await textarea.fill('Check suspension telemetry');
    await sendButton.click();

    // Wait for assistant response
    await expect(
      page.getByText(STANDARD_RESPONSE.answer),
    ).toBeVisible({ timeout: 10000 });

    // Click on evidence source link in the bubble
    const evidenceLink = page.getByRole('button', { name: '1 evidence source' });
    await expect(evidenceLink).toBeVisible();
    await evidenceLink.click();

    // The evidence drawer should now be open — heading is visible
    await expect(
      page.getByRole('heading', { name: 'Evidence' }),
    ).toBeVisible();

    const evidenceDrawer = page.getByRole('complementary', {
      name: 'Evidence drawer',
    });

    // The evidence snippet should be visible inside the drawer
    await expect(
      evidenceDrawer.getByText('Front rebound damping is 25% above optimal range'),
    ).toBeVisible();

    // Groundedness score should be displayed
    await expect(evidenceDrawer.getByText('78%', { exact: true })).toBeVisible();

    // Close the drawer using the close button
    await page.getByRole('button', { name: 'Close evidence drawer' }).click();

    // Drawer heading should disappear
    await expect(
      page.getByRole('heading', { name: 'Evidence' }),
    ).not.toBeVisible();
  });

  test('Evidence drawer toggle floating button appears when evidence exists', async ({
    page,
  }) => {
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(STANDARD_RESPONSE),
      });
    });

    const textarea = page.getByPlaceholder('Ask about telemetry, setup, parts...');
    const sendButton = page.getByRole('button', { name: 'Send message' });

    await textarea.fill('Analyze suspension data');
    await sendButton.click();

    await expect(
      page.getByText(STANDARD_RESPONSE.answer),
    ).toBeVisible({ timeout: 10000 });

    // The floating button should show "Evidence (1)"
    const floatingBtn = page.getByRole('button', { name: 'Evidence (1)' });
    await expect(floatingBtn).toBeVisible();
  });

  test('ModelSelector component is visible in the sidebar', async ({ page }) => {
    // The model select label should be visible on desktop
    await expect(page.getByText('LLM Model')).toBeVisible();

    // The select element should be present
    const modelSelect = page.getByLabel('LLM Model');
    await expect(modelSelect).toBeVisible();

    // It should have the default model selected
    await expect(modelSelect).toHaveValue('qwen2.5:7b');

    // All model options should be present
    const options = await modelSelect.getByRole('option').allTextContents();
    expect(options).toEqual([
      'qwen2.5:7b',
      'qwen2.5:14b',
      'llama3.2:8b',
      'mistral:7b',
      'deepseek-r1:7b',
    ]);
  });

  test('Session context panel shows circuit and session info', async ({ page }) => {
    await expect(page.getByText('Session Context')).toBeVisible();

    // Default values from the store: circuit = 'Jerez', session = 'Practice'
    await expect(page.getByText('Jerez')).toBeVisible();
    await expect(page.getByText('Practice')).toBeVisible();
  });
});
