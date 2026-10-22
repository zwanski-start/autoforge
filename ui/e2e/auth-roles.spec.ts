import { test, expect, type Page } from '@playwright/test'
import type { AuthInfo, Feature, FeatureListResponse, ProjectSummary } from '../src/lib/types'

/**
 * Role-based UI gating (optional auth, see server/utils/auth.py).
 *
 * The whole API is stubbed, so these tests don't need a backend or projects:
 *   cd ui && npm run test:e2e -- auth-roles.spec.ts
 */

const PROJECT = 'demo'

const feature: Feature = {
  id: 1,
  priority: 1,
  category: 'core',
  name: 'Login page',
  description: 'Users can sign in',
  steps: ['Open /login'],
  passes: false,
  in_progress: false,
  dependencies: [],
}

const features: FeatureListResponse = {
  pending: [feature],
  in_progress: [],
  done: [],
  needs_human_input: [],
}

const project: ProjectSummary = {
  name: PROJECT,
  path: '/tmp/demo',
  has_spec: true,
  stats: { passing: 0, in_progress: 0, total: 1, percentage: 0 } as ProjectSummary['stats'],
  default_concurrency: 3,
  auto_improve_enabled: false,
  auto_improve_interval_minutes: 10,
}

function authAs(role: 'viewer' | 'developer'): AuthInfo {
  return {
    enabled: true,
    user: role === 'viewer' ? 'vic' : 'dee',
    groups: [],
    is_admin: false,
    default_role: 'none',
    projects: { [PROJECT]: role },
  }
}

async function stubApi(page: Page, auth: AuthInfo) {
  await page.addInitScript((name) => {
    localStorage.setItem('autoforge-selected-project', name)
    localStorage.setItem('autoforge-active-view', 'kanban')
  }, PROJECT)

  // Live updates aren't needed for these tests
  await page.routeWebSocket(/\/ws\//, (ws) => ws.close())

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const json = (body: unknown) => route.fulfill({ json: body })

    if (path === '/api/auth/me') return json(auth)
    if (path === '/api/setup/status') return json({ claude_cli: true, credentials: true, node: true, npm: true })
    if (path === '/api/projects') return json([project])
    if (path === `/api/projects/${PROJECT}`) return json({ ...project, prompts_dir: '/tmp/demo/prompts' })
    if (path === `/api/projects/${PROJECT}/features`) return json(features)
    if (path === `/api/projects/${PROJECT}/features/graph`) return json({ nodes: [], edges: [] })
    if (path === `/api/projects/${PROJECT}/agent/status`) {
      return json({ status: 'stopped', pid: null, started_at: null, yolo_mode: false })
    }
    if (path === '/api/settings') {
      return json({ yolo_mode: false, model: 'claude-opus-4-6', glm_mode: false, ollama_mode: false,
        testing_agent_ratio: 1, playwright_headless: true, batch_size: 3, testing_batch_size: 3 })
    }
    // Everything else: an empty, successful response
    return json(route.request().method() === 'GET' && path.endsWith('s') ? [] : {})
  })
}

test.describe('Role-based UI gating', () => {
  test.setTimeout(30000)

  test('viewer sees no write actions', async ({ page }) => {
    await stubApi(page, authAs('viewer'))
    await page.goto('/')

    await expect(page.getByText('Login page')).toBeVisible({ timeout: 10000 })

    // Kanban: no add-feature / expand buttons
    await expect(page.locator('button[title="Add new feature (N)"]')).toHaveCount(0)
    await expect(page.locator('button[title="Expand project with AI (E)"]')).toHaveCount(0)

    // N shortcut does not open the add-feature form
    await page.locator('body').press('n')
    await expect(page.getByRole('dialog')).toHaveCount(0)

    // Feature modal: no Edit / Skip / Delete
    await page.getByText('Login page').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Edit' })).toHaveCount(0)
    await expect(dialog.getByRole('button', { name: 'Skip' })).toHaveCount(0)
  })

  test('developer keeps write actions', async ({ page }) => {
    await stubApi(page, authAs('developer'))
    await page.goto('/')

    await expect(page.getByText('Login page')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('button[title="Add new feature (N)"]')).toBeVisible()

    await page.getByText('Login page').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog.getByRole('button', { name: 'Edit' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Skip' })).toBeVisible()
  })
})
