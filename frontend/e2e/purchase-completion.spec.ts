import {test,expect,apiGet,apiPatch,reserveApiSlot} from './fixtures'

test('budget recovery proposes minimum increase and only applies after acceptance',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click()
 await page.locator('.manual-search>summary').click();await page.getByLabel(/^بودجه به تومان/).fill('100')
 await page.getByRole('button',{name:'اعمال شرایط روی همین برنامه'}).click()
 const suggestion=page.getByTestId('constraint-suggestion').filter({hasText:'بودجه'})
 await expect(suggestion).toBeVisible();await expect(page.getByRole('region',{name:'پیشنهاد تغییر یک شرط'})).toContainText('هنوز تغییر نکرده')
 const before=await page.evaluate(()=>localStorage.getItem('plan-b:last-mission'))
 const snapshot=await apiGet(page.request,`/api/missions/${before}`);expect(snapshot.ok()).toBe(true)
 expect((await snapshot.json()).mission.constraints.max_price_toman).toBe('100')
 await suggestion.getByRole('button',{name:'قبول این تغییر'}).click()
 await expect(page.getByTestId('primary-card')).toBeVisible();await expect(page.getByTestId('constraint-suggestion')).toHaveCount(0)
})

test('location chooser selects a recorded address point without silently applying mission',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/')
 await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await expect(page.getByTestId('primary-card')).toBeVisible()
 const missionId=await page.evaluate(()=>localStorage.getItem('plan-b:last-mission'));const before=(await (await apiGet(page.request,`/api/missions/${missionId}`)).json()).mission
 await page.getByRole('button',{name:'انتخاب محدوده'}).click();await page.getByLabel('نام خیابان یا نشانی').fill('جمهوری')
 await page.getByRole('button',{name:'پیدا کردن نشانی'}).click()
 const result=page.getByTestId('location-result').first();await expect(result).toBeVisible();await expect(result).toContainText('نقطه ثبت‌شده در داده')
 const label=(await result.locator('span').innerText()).split('\n')[0]
 await result.click();await expect(page.getByRole('dialog')).toHaveCount(0)
 await expect(page.locator('.origin-control')).toContainText(label)
 const after=(await (await apiGet(page.request,`/api/missions/${missionId}`)).json()).mission;expect(after.constraints).toEqual(before.constraints);expect(after.revision).toBe(before.revision)
 await expect(page.getByRole('status').filter({hasText:'در فرم قرار گرفت'})).toBeVisible()
 await page.locator('.manual-search>summary').click();await page.getByRole('button',{name:'اعمال شرایط روی همین برنامه'}).click();await expect(page.locator('.locked-chips')).toContainText(label)
 const committed=(await (await apiGet(page.request,`/api/missions/${missionId}`)).json()).mission;expect(committed.constraints.origin_label).toBe(label)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
})

test('startup rate limit offers explicit successful retry',async({page})=>{
 let limited=true
 await page.route('**/api/sessions',route=>limited?route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:'rate_limited'})}):route.fallback())
 await page.goto('/');await expect(page.getByRole('button',{name:'تلاش دوباره برای اتصال'})).toBeVisible()
 limited=false;await page.getByRole('button',{name:'تلاش دوباره برای اتصال'}).click()
 await expect(page.getByRole('button',{name:'دیدن سناریوی نمونه'})).toBeEnabled()
})

test('late new mission never steals a later product checkbox focus',async({page})=>{
 let release!:()=>void;const held=new Promise<void>(r=>{release=r})
 let arrived!:()=>void;const started=new Promise<void>(r=>{arrived=r})
 await page.route('**/api/missions',async route=>{arrived();await held;await route.fallback()})
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await started
 const checkbox=page.getByRole('checkbox',{name:'مقایسه',exact:true});await checkbox.focus();await checkbox.press('Space')
 release();await expect(page.getByTestId('primary-card')).toBeVisible();await expect(checkbox).toBeFocused()
})

test('comparison aligns source facts and shows same-condition seller feasibility',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await page.locator('.manual-search>summary').click()
 await page.getByLabel('جست‌وجوی کالا').fill('A07');await page.getByRole('button',{name:'جست‌وجو',exact:true}).click()
 await expect(page.getByTestId('product-card').first()).toBeVisible()
 await page.getByRole('checkbox',{name:'مقایسه',exact:true}).nth(0).check();await page.getByRole('checkbox',{name:'مقایسه',exact:true}).nth(1).check()
 await page.getByRole('button',{name:/مقایسه دو کالا/}).click()
 const dialog=page.getByRole('dialog',{name:'مقایسه دو کالا'});await expect(dialog.getByRole('table')).toBeVisible()
 await expect(dialog.getByRole('row',{name:/فروشگاه سازگار در محدوده/})).toContainText('فروشگاه')
 await expect(dialog.getByRole('row',{name:/موجودی/})).toContainText('نامشخص')
 await expect(dialog.getByRole('row',{name:/ظرفیت باتری/})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
})

test('empty literal search explains a budget mismatch and recovers only on selection',async({page})=>{
 await page.goto('/');await page.locator('.manual-search>summary').click();await page.getByLabel('جست‌وجوی کالا').fill('A07')
 await page.getByLabel(/^بودجه به تومان/).fill('1');await page.getByRole('button',{name:'جست‌وجو',exact:true}).click()
 await expect(page.getByTestId('product-card')).toHaveCount(0);await expect(page.getByRole('button',{name:'جست‌وجو با این بودجه'})).toBeVisible()
 await expect(page.getByLabel(/^بودجه به تومان/)).toHaveValue('1')
 await page.getByRole('button',{name:'جست‌وجو با این بودجه'}).click();await expect(page.getByTestId('product-card').first()).toBeVisible()
})

test('contact-only discovery leads to a real supplied website route without a synthetic phone',async({page})=>{
 await page.goto('/');await page.locator('.manual-search>summary').click();await page.locator('.location-settings>summary').click()
 await page.getByRole('checkbox',{name:'فقط فروشگاه با وب‌سایت یا اینستاگرام ثبت‌شده'}).check()
 // This checks route availability, not visit-time feasibility: include unknown/closed schedules explicitly.
 await page.getByRole('checkbox',{name:'فقط سازگار با ساعت اعلام‌شده'}).uncheck()
 await page.getByLabel('شعاع، کیلومتر').fill('50');await page.getByLabel('جست‌وجوی کالا').fill('A07')
 await page.getByRole('button',{name:'جست‌وجو',exact:true}).click();await expect(page.getByTestId('product-card').first()).toBeVisible()
 await page.getByTestId('product-card').first().getByRole('button',{name:'انتخاب این کالا'}).click()
 await expect(page.getByTestId('primary-card')).toBeVisible()
 await page.getByTestId('primary-card').locator('.source-details>summary').click()
 const route=page.getByTestId('primary-card').getByRole('link',{name:/وب‌سایت ارائه‌شده|اینستاگرام ارائه‌شده/})
 await expect(route).toHaveAttribute('href',/^https?:\/\//)
 expect(await page.locator('a[href^="tel:"]').count()).toBe(0)
})

test('radius recovery only changes radius and retains the chosen origin and budget',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await page.locator('.manual-search>summary').click()
 await page.getByLabel('شعاع، کیلومتر').fill('0.01');await page.locator('.location-settings>summary').click()
 await page.getByLabel('عرض جغرافیایی').fill('35.705');await page.getByRole('button',{name:'اعمال شرایط روی همین برنامه'}).click()
 const suggestion=page.getByTestId('constraint-suggestion').filter({hasText:'شعاع'});await expect(suggestion).toBeVisible()
 await suggestion.getByRole('button',{name:'قبول این تغییر'}).click();await expect(page.getByTestId('primary-card')).toBeVisible()
 const id=await page.evaluate(()=>localStorage.getItem('plan-b:last-mission'));const r=await apiGet(page.request,`/api/missions/${id}`)
 const mission=(await r.json()).mission;expect(mission.constraints.max_price_toman).toBe('40000000');expect(mission.constraints.lat).toBe(35.705)
})

async function compareSamsungContactPair(page: import('@playwright/test').Page){
 await page.goto('/');await page.locator('.manual-search>summary').click();await page.getByLabel('جست‌وجوی کالا').fill('سامسونگ')
 await page.getByRole('combobox',{name:'دسته‌بندی'}).click();await page.getByRole('option',{name:'گوشی موبایل',exact:true}).click()
 await page.locator('.location-settings>summary').click();await page.getByRole('checkbox',{name:'فقط فروشگاه با وب‌سایت یا اینستاگرام ثبت‌شده'}).check()
 await page.getByRole('button',{name:'جست‌وجو',exact:true}).click()
 await page.getByTestId('product-card').filter({hasText:'گوشی سامسونگ Z Flip 7 5G | حافظه 256 رم 12 گیگابایت'}).getByRole('checkbox',{name:'مقایسه'}).check()
 await page.getByTestId('product-card').filter({hasText:'گوشی سامسونگ A57 5G | حافظه 256 رم 8 گیگابایت'}).getByRole('checkbox',{name:'مقایسه'}).check()
 await page.getByRole('button',{name:/مقایسه دو کالا/}).click()
 return page.getByRole('dialog',{name:'مقایسه دو کالا'})
}

test('global comparison prices never reuse contact-filtered search prices',async({page})=>{
 const dialog=await compareSamsungContactPair(page)
 const global=dialog.getByRole('row',{name:/کمترین قیمت کل داده/});await expect(global).toContainText('۲۱۴٬۹۰۰٬۰۰۰');await expect(global).toContainText('۱۳۴٬۰۰۰٬۰۰۰')
 await expect(global).not.toContainText('۳۰۹٬۷۵۲٬۵۰۰')
 const ram=dialog.getByRole('row',{name:/^حافظه رم/});await expect(ram).toHaveCount(1);await expect(ram).toContainText('12 گیگابایت');await expect(ram).toContainText('8 گیگابایت');await expect(ram).toContainText('عنوان منبع: ظرفیت حافظه رم')
 await expect(dialog.locator('.comparison-context')).toContainText('17:00 تهران')
})

test('comparison failure is unknown rather than zero and retries the unchanged snapshot',async({page})=>{
 let fail=true;const bodies:unknown[]=[]
 await page.route('**/api/products/compare',async route=>{bodies.push(route.request().postDataJSON());if(fail)await route.fulfill({status:503,json:{detail:'catalogue_unavailable'}});else await route.fallback()})
 const dialog=await compareSamsungContactPair(page)
 await expect(dialog.getByRole('alert')).toBeVisible();await expect(dialog.getByRole('button',{name:'تلاش دوباره برای مقایسه'})).toBeVisible()
 await expect(dialog.getByRole('row',{name:/فروشگاه سازگار در محدوده/})).toContainText('بررسی انجام نشد')
 await expect(dialog).not.toContainText('گزینه سازگار ثبت نشده');await expect(dialog).not.toContainText('در حال بررسی')
 fail=false;await dialog.getByRole('button',{name:'تلاش دوباره برای مقایسه'}).click();await expect(dialog.getByRole('row',{name:/کمترین قیمت کل داده/})).toContainText('۲۱۴٬۹۰۰٬۰۰۰')
 expect(bodies).toHaveLength(2);expect(bodies[1]).toEqual(bodies[0])
})

test('planned visits default to declared hours and an explicit opt-out persists',async({page})=>{
 await page.goto('/');await page.locator('.manual-search>summary').click();await page.locator('.location-settings>summary').click()
 const hours=page.getByRole('checkbox',{name:'فقط سازگار با ساعت اعلام‌شده'});await expect(hours).toBeChecked()
 await page.getByLabel('زمان مراجعه، تهران').fill('2026-10-23T17:00');await page.getByLabel('جست‌وجوی کالا').fill('A07')
 await page.getByRole('button',{name:'جست‌وجو',exact:true}).click()
 await page.getByTestId('product-card').filter({hasText:'گوشی سامسونگ (چین) A07 4G | حافظه 64 رم 4 گیگابایت'}).getByRole('button',{name:'انتخاب این کالا'}).click()
 await expect(page.getByTestId('primary-card')).not.toContainText('خارج از ساعت اعلام‌شده')
 await hours.uncheck();await page.getByRole('button',{name:'اعمال شرایط روی همین برنامه'}).click()
 await expect(page.getByTestId('primary-card')).toContainText('خارج از ساعت اعلام‌شده')
 await page.reload();await page.locator('.manual-search>summary').click();await page.locator('.location-settings>summary').click();await expect(hours).not.toBeChecked()
})

test('stale recovery refreshes current plan without autoaccepting or discarding draft edits',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await page.locator('.manual-search>summary').click()
 await page.getByLabel(/^بودجه به تومان/).fill('20000000');await page.getByRole('button',{name:'اعمال شرایط روی همین برنامه'}).click();await expect(page.getByTestId('constraint-suggestion').first()).toBeVisible()
 const id=await page.evaluate(()=>localStorage.getItem('plan-b:last-mission'));const initial=(await (await apiGet(page.request,`/api/missions/${id}`)).json()).mission
 const changed=await apiPatch(page.request,`/api/missions/${id}`,{headers:{Origin:new URL(page.url()).origin},data:{expected_revision:initial.revision,constraints:{max_price_toman:'21000000'}}});expect(changed.ok()).toBe(true)
 await page.getByLabel('شعاع، کیلومتر').fill('5')
 await page.getByTestId('constraint-suggestion').first().getByRole('button',{name:'قبول این تغییر'}).click()
 await expect(page.getByRole('button',{name:'تازه‌سازی برنامه'})).toBeVisible();await page.getByRole('button',{name:'تازه‌سازی برنامه'}).click()
 await expect(page.locator('.locked-chips')).toContainText('۲۱٬۰۰۰٬۰۰۰');await expect(page.getByLabel('شعاع، کیلومتر')).toHaveValue('5')
 const after=(await (await apiGet(page.request,`/api/missions/${id}`)).json()).mission;expect(after.constraints.max_price_toman).toBe('21000000');expect(after.revision).toBe(initial.revision+1)
 await expect(page.getByTestId('constraint-suggestion').first()).toContainText('۱۸٬۲۰۰٬۰۰۰')
})


test('pending sample load cannot overwrite a later manual budget edit',async({page})=>{
 let release!:()=>void;const held=new Promise<void>(r=>{release=r})
 let arrived!:()=>void;const started=new Promise<void>(r=>{arrived=r})
 await page.route('**/api/products/product_adfdc73bc839d15cd7754318',async route=>{arrived();await held;await route.fallback()})
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await started
 await page.locator('.manual-search>summary').click();const budget=page.getByLabel(/^بودجه به تومان/)
 const disabled=await budget.isDisabled();release();expect(disabled).toBe(true)
 await expect(page.getByTestId('primary-card')).toBeVisible();await expect(budget).toBeEnabled();await budget.fill('100');await expect(budget).toHaveValue('100')
})


test('late condition save preserves a newer selected origin as an uncommitted draft',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await expect(page.getByTestId('primary-card')).toBeVisible()
 const id=await page.evaluate(()=>localStorage.getItem('plan-b:last-mission'))
 let release!:()=>void;const held=new Promise<void>(r=>{release=r})
 let arrived!:()=>void;const started=new Promise<void>(r=>{arrived=r});let writes=0
 await page.route(`**/api/missions/${id}`,async route=>{
  if(route.request().method()!=='PATCH'){await route.fallback();return}
  writes++;await reserveApiSlot();const response=await route.fetch();arrived();await held;await route.fulfill({response})
 })
 await page.locator('.manual-search>summary').click();await page.getByRole('button',{name:'اعمال شرایط روی همین برنامه'}).click();await started
 await page.getByRole('button',{name:'انتخاب محدوده'}).click();await page.getByLabel('نام خیابان یا نشانی').fill('تجریش');await page.getByRole('button',{name:'پیدا کردن نشانی'}).click()
 const result=page.getByTestId('location-result').first();await expect(result).toBeVisible();const label=(await result.locator('span').innerText()).split('\n')[0]
 await result.click();await expect(page.locator('.origin-control')).toContainText(label)
 release();await expect(page.getByRole('button',{name:'اعمال شرایط روی همین برنامه'})).toBeEnabled()
 await expect(page.locator('.origin-control')).toContainText(label);await expect(page.locator('.locked-chips')).toContainText('محدوده جمهوری')
 const persisted=(await (await apiGet(page.request,`/api/missions/${id}`)).json()).mission
 expect(persisted.constraints.lat).toBe(35.69508821734553);expect(persisted.constraints.origin_label).toBe('محدوده جمهوری (نقطه پیش‌فرض)');expect(writes).toBe(1)
})

test('late sample loading preserves a newer origin separately from its sample mission',async({page})=>{
 let release!:()=>void;const held=new Promise<void>(r=>{release=r})
 let arrived!:()=>void;const started=new Promise<void>(r=>{arrived=r})
 await page.route('**/api/products/product_adfdc73bc839d15cd7754318',async route=>{arrived();await held;await route.fallback()})
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await started
 await page.getByRole('button',{name:'انتخاب محدوده'}).click();await page.getByLabel('نام خیابان یا نشانی').fill('تجریش');await page.getByRole('button',{name:'پیدا کردن نشانی'}).click()
 const result=page.getByTestId('location-result').first();await expect(result).toBeVisible();const label=(await result.locator('span').innerText()).split('\n')[0]
 await result.click();await expect(page.locator('.origin-control')).toContainText(label)
 release();await expect(page.getByTestId('primary-card')).toBeVisible()
 await expect(page.locator('.origin-control')).toContainText(label);await expect(page.locator('.locked-chips')).toContainText('محدوده جمهوری')
})
