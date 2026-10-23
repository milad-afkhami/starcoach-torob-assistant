import {test,expect} from './fixtures'

test('agent is the first useful mobile input, with search still available',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/')
 const composer=page.getByLabel('نیاز شما');await expect(composer).toBeInViewport()
 const composerBox=await composer.boundingBox();await page.locator('.manual-search>summary').click();const searchBox=await page.getByLabel('جست‌وجوی کالا').boundingBox()
 expect(composerBox!.y).toBeLessThan(searchBox!.y)
 await expect(page.getByRole('region',{name:'گفت‌وگوی خرید'})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
})
test('search composite owns a single visible focus treatment',async({page})=>{
 await page.goto('/');await page.locator('.manual-search>summary').click();const input=page.getByLabel('جست‌وجوی کالا');await input.focus()
 expect(await input.evaluate(x=>getComputedStyle(x).outlineStyle)).toBe('none')
 expect(await page.locator('.search-row').evaluate(x=>getComputedStyle(x).boxShadow)).not.toBe('none')
})
test('designed select supports keyboard choice escape and disabled choices',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click()
 await page.getByTestId('primary-card').getByRole('button',{name:'بررسی پاسخ فروشنده'}).click()
 const select=page.getByRole('combobox',{name:'نتیجه بررسی'});await select.focus();await select.press('ArrowDown')
 await expect(page.getByRole('listbox')).toBeVisible();await select.press('End');await select.press('Enter')
 await expect(select).toContainText('فروشگاه تعطیل است');await expect(page.getByRole('listbox')).toHaveCount(0)
 await select.press('ArrowDown');await select.press('Escape');await expect(select).toBeFocused()
 await select.click();await expect(page.getByRole('option',{name:'شرط پرداخت پذیرفته نشد'})).toHaveAttribute('aria-disabled','true')
 await page.getByRole('option',{name:'ناموجود',exact:true}).click();await expect(select).toContainText('ناموجود')
})

test('comparison checkbox retains keyboard semantics and designed appearance',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click()
 const box=page.getByRole('checkbox',{name:'مقایسه',exact:true});await box.focus();await box.press('Space')
 await expect(box).toBeChecked();await expect(box).toBeFocused()
 expect(await box.evaluate(x=>getComputedStyle(x).appearance)).toBe('none')
 await box.press('Space');await expect(box).not.toBeChecked()
})

test('excluded sellers are grouped by the reason instead of one unbounded list',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click()
 await page.locator('.excluded-list>summary').click()
 await expect(page.locator('.excluded-group').first()).toBeVisible()
 await expect(page.getByTestId('excluded-card').first()).not.toBeInViewport()
 await page.locator('.excluded-group>summary').first().click()
 await expect(page.getByTestId('excluded-card').first()).toBeVisible()
})
