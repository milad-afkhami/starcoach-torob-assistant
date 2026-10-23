import {test,expect} from './fixtures'

test.skip(!process.env.DISCOVERY_FIXTURE,'Requires isolated deterministic no-model worker')

test('welcome is a chat and each response remains in the timeline',async({page})=>{
 await page.goto('/');await expect(page.getByRole('heading',{name:'برای خرید چی در نظر داری؟'})).toBeVisible()
 await expect(page.locator('.mission-panel')).toHaveCount(0)
 const composer=page.getByLabel('نیاز شما');await composer.fill('گوشی A07');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.getByTestId('product-card').first()).toBeVisible()
 await expect(page.locator('.chat-message.user').first()).toContainText('گوشی A07')
 await composer.fill('دومی را با اولی مقایسه کن');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.locator('.inline-comparison')).toBeVisible()
 await expect(page.locator('.chat-message.user')).toHaveCount(2)
 await expect(page.locator('.chat-message.assistant').first().locator('.product-card').first()).toBeVisible()
})

test('sample embeds a real geographic shop map with equivalent keyboard list',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click()
 await expect(page.getByTestId('simulation-banner')).toBeVisible()
 await expect(page.locator('.shop-map .leaflet-container')).toBeVisible()
 await expect(page.locator('.shop-map .leaflet-marker-icon')).toHaveCount(2)
 await expect(page.locator('.shop-map')).toContainText('OpenStreetMap')
 const backup=page.locator('.map-shop-list button').filter({hasText:'گزینه دوم'})
 await backup.focus();await page.keyboard.press('Enter');await expect(backup).toHaveAttribute('aria-pressed','true')
 await expect(page.locator('.map-selection')).toContainText('گزینه دوم')
})

test('map failure keeps source addresses and explicitly warns',async({page})=>{
 await page.route('https://tile.openstreetmap.org/**',r=>r.abort())
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click()
 await expect(page.locator('.map-failure')).toContainText('نقشه زمینه')
 await expect(page.locator('.map-shop-list button')).toHaveCount(2)
 await expect(page.locator('.shop-map .leaflet-marker-icon')).toHaveCount(2)
})

test('mobile welcome and composer stay within the viewport',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/')
 await expect(page.getByLabel('نیاز شما')).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 const box=await page.getByLabel('نیاز شما').boundingBox();expect(box!.y+box!.height).toBeLessThan(844)
})

test('Enter sends once, Shift Enter inserts a line, and IME Enter does not send',async({page})=>{
 await page.goto('/');const input=page.getByLabel('نیاز شما');let starts=0
 page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname==='/api/turns')starts++})
 await input.fill('گوشی A07');await input.press('Shift+Enter');await expect(input).toHaveValue('گوشی A07\n')
 await input.dispatchEvent('keydown',{key:'Enter',code:'Enter',isComposing:true});expect(starts).toBe(0)
 await input.press('Enter');await expect(page.getByTestId('product-card').first()).toBeVisible();expect(starts).toBe(1);await expect(input).toBeEmpty()
})

test('fresh conversation clears the plan, proposals, draft and continuation without deleting audit state',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await expect(page.getByTestId('primary-card')).toBeVisible()
 await page.getByRole('button',{name:'رفتن به فروشگاه'}).click();await expect(page.locator('.transport-panel')).toBeVisible()
 await page.getByRole('button',{name:'گفت‌وگوی تازه'}).click()
 await expect(page.getByRole('heading',{name:'برای خرید چی در نظر داری؟'})).toBeVisible();await expect(page.locator('.chat-message')).toHaveCount(0)
 await expect(page.locator('.mission-panel,.transport-panel,.proposal')).toHaveCount(0)
 expect(await page.evaluate(()=>localStorage.getItem('plan-b:last-mission'))).toBeNull()
 await page.locator('.manual-search>summary').click();await expect(page.getByLabel(/^بودجه به تومان/)).toHaveValue('')
 let parent:unknown='uncaptured';page.on('request',r=>{if(new URL(r.url()).pathname==='/api/turns')parent=r.postDataJSON().discovery_parent_turn_id})
 await page.getByLabel('نیاز شما').fill('دومی را با اولی مقایسه کن');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.locator('.ai-message')).toContainText('ابتدا گزینه‌ها');expect(parent).toBeUndefined()
})

test('fresh conversation cancels a pending initial turn and rejects its late completion',async({page})=>{
 let release!:()=>void;const held=new Promise<void>(r=>{release=r})
 await page.route('**/api/turns',async route=>{await held;await route.fulfill({json:{id:'fresh-late',state:'completed',stage:'interpret',result:{products:[],recommendations:[],clarification_fa:'OBSOLETE_FRESH_RESULT',proposed_constraints:{}}}})})
 await page.route('**/api/turns/fresh-late/cancel',r=>r.fulfill({json:{state:'canceled'}}))
 await page.goto('/');await page.getByLabel('نیاز شما').fill('گوشی A07');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.getByRole('button',{name:'توقف بررسی'})).toBeVisible();await page.getByRole('button',{name:'گفت‌وگوی تازه'}).click()
 release();await expect(page.getByRole('heading',{name:'برای خرید چی در نظر داری؟'})).toBeVisible();await expect(page.getByText('OBSOLETE_FRESH_RESULT')).toHaveCount(0)
})

test('reload restores only an owned plan and clearly says previous chat was not restored',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await expect(page.getByTestId('primary-card')).toBeVisible()
 await page.reload();await expect(page.getByTestId('primary-card')).toBeVisible();await expect(page.locator('.chat-message')).toHaveCount(1)
 await expect(page.locator('.message-text')).toContainText('پیام‌های گفت‌وگوی قبلی');await expect(page.locator('.proposal')).toHaveCount(0)
})

test('ordinary no-match uses the conversation and keeps search repair accessible',async({page})=>{
 await page.goto('/');await page.locator('.manual-search>summary').click();await page.getByLabel('جست‌وجوی کالا').fill('zznotacatalogueitemzz')
 await page.getByRole('button',{name:'جست‌وجو',exact:true}).click();await expect(page.locator('.chat-message.assistant')).toContainText('نتیجه‌ای پیدا نشد')
 await expect(page.getByTestId('product-card')).toHaveCount(0);await expect(page.getByLabel('نیاز شما')).toBeVisible()
})

test('new message with a visible plan preserves its revision until explicit approval',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await expect(page.getByTestId('primary-card')).toBeVisible()
 const before=await page.locator('.locked-chips').innerText()
 await page.getByRole('combobox',{name:'موضوع درخواست'}).click();await page.getByRole('option',{name:'شرایط همین کالا',exact:true}).click()
 await page.getByLabel('نیاز شما').fill('گزینه‌های همین کالا را بررسی کن');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.locator('.proposal')).toBeVisible();expect(await page.locator('.locked-chips').innerText()).toBe(before)
 await expect(page.getByTestId('primary-card')).toBeVisible()
})

test('the reply closing text and actions can scroll fully above the composer',async({page})=>{
 await page.setViewportSize({width:1440,height:1000});await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await expect(page.getByTestId('primary-card')).toBeVisible()
 await page.evaluate(()=>scrollTo(0,document.body.scrollHeight))
 const bounds=await page.evaluate(()=>({closing:[...document.querySelectorAll('.message-next')].at(-1)!.getBoundingClientRect().bottom,composer:document.querySelector('.chat-composer')!.getBoundingClientRect().top}))
 expect(bounds.closing).toBeLessThan(bounds.composer)
})

test('map marker keyboard selection matches the list without changing the purchase destination',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await expect(page.getByTestId('primary-card')).toBeVisible()
 const primary=await page.getByTestId('primary-card').locator('h3').innerText()
 const backup=page.locator('.leaflet-marker-icon.fallback');await backup.focus();await backup.press('Enter')
 await expect(backup).toHaveAttribute('aria-pressed','true');await expect(page.locator('.map-shop-list button.fallback')).toHaveAttribute('aria-pressed','true')
 await page.getByRole('button',{name:'رفتن به فروشگاه'}).click();await expect(page.locator('.transport-panel')).toContainText('مقصد گزینه اول');await expect(page.getByTestId('primary-card').locator('h3')).toHaveText(primary)
})

test('ordinary assistant no-match and help replies stay usable in one conversation',async({page})=>{
 await page.goto('/');await page.getByLabel('نیاز شما').fill('یک کالای بدون نتیجه پیدا کن');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.locator('.chat-message.assistant').first()).toBeVisible();await expect(page.getByRole('button',{name:'توقف بررسی'})).toHaveCount(0)
 await expect(page.getByTestId('product-card')).toHaveCount(0)
 await page.getByLabel('نیاز شما').fill('کمکم کن');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.locator('.ai-message')).toContainText('چه کالایی');await expect(page.locator('.chat-message.user')).toHaveCount(2)
 await expect(page.getByRole('button',{name:'کمک برای انتخاب'})).toBeEnabled()
})
