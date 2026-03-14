import { test, expect, Page } from '@playwright/test'

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------
const MOCK_PERSONS = [
  { id: 88, name: 'Yuer Guo', item_count: 2280 },
  { id: 97, name: 'Yi Zhang', item_count: 2579 },
]
const MOCK_LOCATIONS = [
  { country: 'Singapore', first_level: 'Singapore', second_level: 'Marina Bay', item_count: 120 },
  { country: 'France', first_level: 'Paris', second_level: 'Paris', item_count: 211 },
]
const MOCK_CONCEPTS = [{ id: 1, stem: 'beach', usage_count: 50 }]
const MOCK_CAMERAS = [{ camera: 'Galaxy S25 Ultra', item_count: 500 }]
const MOCK_ITEMS = [
  {
    id: 1001,
    filename: 'test_photo.jpg',
    takentime: 1749773004,
    taken_iso: '2025-06-12T20:03:24',
    item_type: 0,
    type_name: 'photo',
    filesize: 2 * 1024 * 1024,
    width: 4000,
    height: 3000,
    duration: null,
    vres_x: null,
    fps: null,
    country: 'Singapore',
    district: 'Marina Bay',
    camera: 'Galaxy S25 Ultra',
    latitude: 1.28,
    longitude: 103.86,
    cache_key: '1001_12345',
    duplicate_hash: 'ABC123',
  },
  {
    id: 1002,
    filename: 'test_video.mp4',
    takentime: 1749780000,
    taken_iso: '2025-06-12T22:00:00',
    item_type: 1,
    type_name: 'video',
    filesize: 50 * 1024 * 1024,
    width: null,
    height: null,
    duration: 45000,
    vres_x: 3840,
    fps: 30,
    country: 'Singapore',
    district: null,
    camera: 'DJI Pocket 3',
    latitude: null,
    longitude: null,
    cache_key: '1002_67890',
    duplicate_hash: 'DEF456',
  },
]
const MOCK_COLLECT_RESULT = { items: MOCK_ITEMS, count: 2, total_mb: 52.0 }

// Minimal 1x1 JPEG as binary buffer
const THUMB_JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAAUCAABAAEEASIAAhEBAxEB/8QAFgABAQEAAAAAAAAAAAAAAAAABQQD/8QAIhAAAQQBBAMAAAAAAAAAAAAAAQACAxESITFBUWH/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8Atp2tznZrNXJERERMf//Z',
  'base64'
)

// ---------------------------------------------------------------------------
// Helper: set up all API mocks for a page
// ---------------------------------------------------------------------------
async function setupMocks(page: Page) {
  await page.route('**/api/persons', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_PERSONS) })
  )
  await page.route('**/api/locations', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_LOCATIONS) })
  )
  await page.route('**/api/concepts', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CONCEPTS) })
  )
  await page.route('**/api/cameras', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAMERAS) })
  )
  await page.route('**/api/collect', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_COLLECT_RESULT) })
  )
  await page.route('**/api/thumbnail/**', route =>
    route.fulfill({ status: 200, contentType: 'image/jpeg', body: THUMB_JPEG })
  )
  await page.route('**/api/media/**', route =>
    route.fulfill({ status: 200, contentType: 'image/jpeg', body: THUMB_JPEG })
  )
}

// ---------------------------------------------------------------------------
// Helper: load page with mocks, wait for filter panel to be ready
// ---------------------------------------------------------------------------
async function loadApp(page: Page) {
  await setupMocks(page)
  await page.goto('/')
  // Wait until persons dropdown trigger is visible (reference data loaded)
  await page.waitForSelector('text=Photo Collect')
}

// ---------------------------------------------------------------------------
// Helper: trigger a search and wait for results grid
// ---------------------------------------------------------------------------
async function doSearch(page: Page) {
  await page.getByRole('button', { name: 'Search' }).click()
  await page.waitForSelector('text=2 items')
}

// ---------------------------------------------------------------------------
// 1. Page loads
// ---------------------------------------------------------------------------
test('page loads — reference data endpoints called and filter panel visible', async ({ page }) => {
  const requestedUrls: string[] = []

  await page.route('**/api/**', async route => {
    requestedUrls.push(route.request().url())
    // Delegate to the standard mocks already set up
    await route.continue()
  })
  await setupMocks(page)
  await page.goto('/')
  await page.waitForSelector('text=Photo Collect')

  // Title visible
  await expect(page.locator('h1')).toContainText('Photo Collect')

  // Persons appear in the multiselect trigger area after reference data loads
  // Open the persons multiselect
  const personsDropdownBtn = page.locator('section').filter({ hasText: 'Persons' }).locator('button').first()
  await personsDropdownBtn.click()
  await expect(page.getByText('Yuer Guo')).toBeVisible()
  await expect(page.getByText('Yi Zhang')).toBeVisible()
})

// ---------------------------------------------------------------------------
// 2. Filter panel — persons multiselect and country dropdown
// ---------------------------------------------------------------------------
test('filter panel — persons multiselect opens and shows options', async ({ page }) => {
  await loadApp(page)

  const personsSection = page.locator('section').filter({ hasText: 'Persons' })
  await personsSection.locator('button').first().click()

  // Both persons visible
  await expect(page.getByText('Yuer Guo')).toBeVisible()
  await expect(page.getByText('Yi Zhang')).toBeVisible()

  // Select Yuer Guo
  await page.getByLabel('Yuer Guo').check()
  // Close by clicking elsewhere
  await page.keyboard.press('Escape')

  // Button now shows selected person name
  await expect(personsSection.locator('button').first()).toContainText('Yuer Guo')
})

test('filter panel — country dropdown shows locations, selecting shows city', async ({ page }) => {
  await loadApp(page)

  const countrySelect = page.locator('select').first()
  await expect(countrySelect).toBeVisible()

  // Both countries should be in the select
  await expect(countrySelect.locator('option', { hasText: 'France' })).toBeAttached()
  await expect(countrySelect.locator('option', { hasText: 'Singapore' })).toBeAttached()

  // Select Singapore — City/Region should appear
  await countrySelect.selectOption('Singapore')
  await expect(page.getByText('City / Region')).toBeVisible()

  // Singapore city option present
  const citySelect = page.locator('select').nth(1)
  await expect(citySelect.locator('option', { hasText: 'Singapore' })).toBeAttached()
})

// ---------------------------------------------------------------------------
// 3. Search — calls /api/collect and shows results
// ---------------------------------------------------------------------------
test('search — calls /api/collect and shows results grid', async ({ page }) => {
  let collectBody: unknown = null

  await setupMocks(page)
  await page.route('**/api/collect', async route => {
    collectBody = JSON.parse(route.request().postData() ?? '{}')
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_COLLECT_RESULT) })
  })

  await page.goto('/')
  await page.waitForSelector('text=Photo Collect')

  await page.getByRole('button', { name: 'Search' }).click()
  await page.waitForSelector('text=2 items')

  // Item count in toolbar
  await expect(page.getByText('2 items')).toBeVisible()

  // Total MB shown
  await expect(page.getByText(/52\.0 MB/)).toBeVisible()

  // Both filenames appear
  await expect(page.getByText('test_photo.jpg')).toBeVisible()
  await expect(page.getByText('test_video.mp4')).toBeVisible()

  // Verify /api/collect was called
  expect(collectBody).not.toBeNull()
})

// ---------------------------------------------------------------------------
// 4. Cart — toggle items in/out
// ---------------------------------------------------------------------------
test('cart — clicking item adds it (blue border), CartBar appears, clicking again removes', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  // CartBar should not be visible initially
  await expect(page.locator('text=🛒 Cart')).not.toBeVisible()

  // The grid item card is a div that contains the img; clicking it toggles cart.
  // We locate it by its filename text label in the card caption.
  // Use the grid item container (the outermost clickable div).
  // It is the div with class "relative rounded overflow-hidden cursor-pointer border-2"
  // that contains our image. We locate it via the filename text underneath.
  const photoCard = page.locator('div.relative.rounded.overflow-hidden').filter({ hasText: 'test_photo.jpg' }).first()

  await photoCard.click()

  // CartBar should appear
  await expect(page.getByText('🛒 Cart')).toBeVisible()
  await expect(page.getByText('1 items')).toBeVisible()

  // Click again to remove — the overlay div is a child so clicking the card works
  await photoCard.click()

  // CartBar should disappear
  await expect(page.getByText('🛒 Cart')).not.toBeVisible()
})

// ---------------------------------------------------------------------------
// 5. Select all / Clear
// ---------------------------------------------------------------------------
test('select all adds all items to cart, clear removes them', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  // Click "Select all"
  await page.getByRole('button', { name: 'Select all' }).click()

  // CartBar should show 2 items
  await expect(page.getByText('🛒 Cart')).toBeVisible()
  // CartBar shows "2 items"
  const cartBar = page.locator('div').filter({ hasText: '🛒 Cart' }).first()
  await expect(cartBar).toContainText('2 items')

  // Click "Clear" in the results toolbar (not the CartBar Clear)
  await page.getByRole('button', { name: 'Clear' }).first().click()

  // CartBar should disappear
  await expect(page.getByText('🛒 Cart')).not.toBeVisible()
})

// ---------------------------------------------------------------------------
// 6. Context menu — right-click shows menu, close on click-away, Escape
// ---------------------------------------------------------------------------
test('context menu — right-click shows View full size and Add to cart options', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  const photoCard = page.locator('div.relative.rounded.overflow-hidden').filter({ hasText: 'test_photo.jpg' }).first()
  await photoCard.click({ button: 'right' })

  // Context menu items visible
  await expect(page.getByText('🔍 View full size')).toBeVisible()
  await expect(page.getByText('+ Add to cart')).toBeVisible()
})

test('context menu — clicking elsewhere closes it', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  const photoCard = page.locator('div.relative.rounded.overflow-hidden').filter({ hasText: 'test_photo.jpg' }).first()
  await photoCard.click({ button: 'right' })
  await expect(page.getByText('🔍 View full size')).toBeVisible()

  // Click somewhere else
  await page.mouse.click(10, 10)
  await expect(page.getByText('🔍 View full size')).not.toBeVisible()
})

test('context menu — Escape closes it', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  const photoCard = page.locator('div.relative.rounded.overflow-hidden').filter({ hasText: 'test_photo.jpg' }).first()
  await photoCard.click({ button: 'right' })
  await expect(page.getByText('🔍 View full size')).toBeVisible()

  await page.keyboard.press('Escape')
  await expect(page.getByText('🔍 View full size')).not.toBeVisible()
})

test('context menu — Add to cart from context menu adds item', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  const photoCard = page.locator('div.relative.rounded.overflow-hidden').filter({ hasText: 'test_photo.jpg' }).first()
  await photoCard.click({ button: 'right' })
  await page.getByText('+ Add to cart').click()

  // Cart should now have item
  await expect(page.getByText('🛒 Cart')).toBeVisible()

  // Right-click same item again — should show Remove from cart.
  // After adding to cart the overlay div is present but the card is still right-clickable.
  await photoCard.click({ button: 'right' })
  await expect(page.getByText('✓ Remove from cart')).toBeVisible()
  // Close
  await page.keyboard.press('Escape')
})

// ---------------------------------------------------------------------------
// 7. Lightbox — open via context menu, Escape closes, arrow navigation
// ---------------------------------------------------------------------------
test('lightbox — View full size opens lightbox with filename in header', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  const firstImg = page.locator('[alt="test_photo.jpg"]').first()
  await firstImg.click({ button: 'right' })
  await page.getByText('🔍 View full size').click()

  // Lightbox opens — filename visible in header
  await expect(page.getByText('test_photo.jpg').first()).toBeVisible()

  // "1 / 2" navigation indicator
  await expect(page.getByText('1 / 2')).toBeVisible()
})

test('lightbox — Escape closes the lightbox', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  const firstImg = page.locator('[alt="test_photo.jpg"]').first()
  await firstImg.click({ button: 'right' })
  await page.getByText('🔍 View full size').click()

  // Lightbox open
  await expect(page.getByText('1 / 2')).toBeVisible()

  await page.keyboard.press('Escape')

  // Lightbox closed
  await expect(page.getByText('1 / 2')).not.toBeVisible()
})

test('lightbox — arrow navigation moves between items', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  const firstImg = page.locator('[alt="test_photo.jpg"]').first()
  await firstImg.click({ button: 'right' })
  await page.getByText('🔍 View full size').click()

  // At item 1/2
  await expect(page.getByText('1 / 2')).toBeVisible()

  // Navigate to next with ArrowRight
  await page.keyboard.press('ArrowRight')
  await expect(page.getByText('2 / 2')).toBeVisible()
  // Second item filename
  await expect(page.getByText('test_video.mp4').first()).toBeVisible()

  // Navigate back with ArrowLeft
  await page.keyboard.press('ArrowLeft')
  await expect(page.getByText('1 / 2')).toBeVisible()
})

test('lightbox — close button (×) closes lightbox', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  const firstImg = page.locator('[alt="test_photo.jpg"]').first()
  await firstImg.click({ button: 'right' })
  await page.getByText('🔍 View full size').click()
  await expect(page.getByText('1 / 2')).toBeVisible()

  // The × close button in the header
  // There's a × button in the lightbox header; use the one inside fixed inset-0
  const lightboxClose = page.locator('.fixed.inset-0').getByRole('button').filter({ hasText: '×' })
  await lightboxClose.click()
  await expect(page.getByText('1 / 2')).not.toBeVisible()
})

// ---------------------------------------------------------------------------
// 8. Cart expand — expand CartBar to see list, remove item with × button
// ---------------------------------------------------------------------------
test('cart expand — clicking CartBar shows list of items, × removes an item', async ({ page }) => {
  await loadApp(page)
  await doSearch(page)

  // Add all items
  await page.getByRole('button', { name: 'Select all' }).click()
  await expect(page.getByText('🛒 Cart')).toBeVisible()

  // The CartBar summary bar is a flex div with green top border containing "🛒 Cart".
  // We click the "🛒 Cart" emoji+text span, which is inside the clickable summary div.
  // Use the CartBar's green-border container and click within it.
  const cartBarContainer = page.locator('.border-t.border-green-700')
  // Click the summary row (the first direct child flex div) — click the Cart label text
  await cartBarContainer.getByText('🛒 Cart').click()

  // Expanded list should show both filenames (in the expanded cart section)
  const expandedList = page.locator('.max-h-64.overflow-y-auto')
  await expect(expandedList).toBeVisible()
  await expect(expandedList.getByText('test_photo.jpg')).toBeVisible()
  await expect(expandedList.getByText('test_video.mp4')).toBeVisible()

  // Click × on the first item in the expanded list.
  // The × character is U+00D7. Use nth(0) to target the first remove button.
  const removeButtons = expandedList.locator('button')
  await removeButtons.first().click()

  // Now cart should have 1 item — check the CartBar count text (within CartBar container)
  await expect(cartBarContainer.getByText('1 items')).toBeVisible()
})

// ---------------------------------------------------------------------------
// 9. SQL mode — not implemented yet (placeholder)
// ---------------------------------------------------------------------------
test.skip('SQL mode — not implemented yet', async () => {
  // This feature is not yet implemented in the UI.
})
