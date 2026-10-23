import {test,expect} from './fixtures'

test('a dropped polling read recovers the same typed reply preview with exactly one turn POST',async({page})=>{
 let posts=0,reads=0,confirmations=0
 await page.route('**/api/capabilities',route=>route.fulfill({json:{catalogue_ready:true,model_available:true}}))
 await page.route('**/api/turns',route=>{posts++;return route.fulfill({json:{id:'controlled-read-loss',state:'running',stage:'reply',result:null}})})
 await page.route('**/api/turns/controlled-read-loss',route=>{if(++reads===1)return route.abort('failed');return route.fulfill({json:{id:'controlled-read-loss',state:'completed',stage:'reply',result:{products:[],recommendations:[],clarification_fa:'برداشت آماده بررسی است.',proposed_constraints:{},observation:{id:'same-controlled-preview',kind:'unavailable',base_revision:1,raw_text:'CONTROLLED typed seller reply',price_toman:null,effective_visit_date:null,provenance:'simulation'},degraded:false}}})})
 page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/confirm'))confirmations++})
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await expect(page.getByTestId('simulation-banner')).toBeVisible()
 await page.getByTestId('primary-card').getByRole('button',{name:'بررسی پاسخ فروشنده'}).click();await page.getByLabel('متن پاسخ فروشنده').fill('این مدل موجود نیست')
 await page.getByRole('button',{name:'برداشت دستیار از پاسخ'}).click()
 await expect(page.getByTestId('observation-preview')).toContainText('هنوز اعمال نشده');await expect(page.getByTestId('observation-preview')).toContainText('CONTROLLED typed seller reply')
 expect(posts).toBe(1);expect(reads).toBe(2);expect(confirmations).toBe(0)
 await expect(page.getByTestId('primary-card')).toContainText('۳۹٬۲۰۰٬۰۰۰')
})

test('persistent polling transport loss stops after three retries and never creates another turn',async({page})=>{
 let posts=0,reads=0
 await page.route('**/api/capabilities',route=>route.fulfill({json:{catalogue_ready:true,model_available:true}}))
 await page.route('**/api/turns',route=>{posts++;return route.fulfill({json:{id:'persistent-controlled',state:'running',stage:'interpret',result:null}})})
 await page.route('**/api/turns/persistent-controlled',route=>{reads++;return route.abort('failed')})
 await page.goto('/');await page.getByLabel('نیاز شما').fill('CONTROLLED no model call');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.getByRole('button',{name:'توقف بررسی'})).toHaveCount(0,{timeout:10000})
 await expect(page.getByText('ارتباط برقرار نشد؛ دوباره تلاش کنید.',{exact:true})).toBeVisible()
 expect(posts).toBe(1);expect(reads).toBe(4);await page.waitForTimeout(700);expect(reads).toBe(4)
})

test('cancel during a polling retry prevents a completed stale result from returning',async({page})=>{
 let posts=0,reads=0,cancels=0,failed!:()=>void
 const failure=new Promise<void>(r=>{failed=r})
 await page.route('**/api/capabilities',route=>route.fulfill({json:{catalogue_ready:true,model_available:true}}))
 await page.route('**/api/turns',route=>{posts++;return route.fulfill({json:{id:'cancel-controlled',state:'running',stage:'interpret',result:null}})})
 await page.route('**/api/turns/cancel-controlled/cancel',route=>{cancels++;return route.fulfill({json:{state:'canceled'}})})
 await page.route('**/api/turns/cancel-controlled',async route=>{reads++;await route.abort('failed');failed()})
 await page.goto('/');await page.getByLabel('نیاز شما').fill('CONTROLLED no model call');await page.getByRole('button',{name:'کمک برای انتخاب'}).click();await failure
 await page.getByRole('button',{name:'توقف بررسی'}).click();await expect(page.getByRole('button',{name:'توقف بررسی'})).toHaveCount(0)
 await page.waitForTimeout(1200);expect(posts).toBe(1);expect(reads).toBe(1);expect(cancels).toBe(1);await expect(page.locator('.discovery-context')).toHaveCount(0)
})

test('turn creation transport loss is not retried and does not start polling',async({page})=>{
 let posts=0,reads=0
 await page.route('**/api/capabilities',route=>route.fulfill({json:{catalogue_ready:true,model_available:true}}))
 await page.route('**/api/turns',route=>{posts++;return route.abort('failed')})
 page.on('request',r=>{if(r.method()==='GET'&&/\/api\/turns\//.test(new URL(r.url()).pathname))reads++})
 await page.goto('/');await page.getByLabel('نیاز شما').fill('CONTROLLED no model call');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.getByText('ارتباط برقرار نشد؛ دوباره تلاش کنید.',{exact:true})).toBeVisible();await page.waitForTimeout(700)
 expect(posts).toBe(1);expect(reads).toBe(0)
})
