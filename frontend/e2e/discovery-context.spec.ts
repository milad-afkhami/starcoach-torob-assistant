import {test,expect,reserveApiSlot} from './fixtures'

test.skip(!process.env.DISCOVERY_FIXTURE,'Requires explicitly isolated no-model fixture-worker server')

test('follow-up compares exact previous displayed cards through actual owned HTTP context',async({page})=>{
 await page.goto('/');await expect(page.getByRole('button',{name:'کمک برای انتخاب'})).toBeEnabled()
 await page.getByLabel('نیاز شما').fill('دو گوشی A07 را نشان بده');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.getByTestId('product-card').first()).toBeVisible();await expect(page.getByRole('button',{name:'توقف بررسی'})).toHaveCount(0)
 const titles=await page.getByTestId('product-card').locator('h3').allTextContents()
 const bodies:Record<string,unknown>[]=[]
 page.on('request',r=>{if(new URL(r.url()).pathname==='/api/turns')bodies.push(r.postDataJSON())})
 await page.getByLabel('نیاز شما').fill('دومی را با اولی از نظر حافظه و بودجه مقایسه کن');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.getByRole('button',{name:'مقایسه همین دو گزینه'})).toBeVisible()
 expect(bodies.at(-1)?.discovery_parent_turn_id).toBeTruthy()
 await page.getByRole('button',{name:'مقایسه همین دو گزینه'}).click()
 const dialog=page.getByRole('dialog',{name:'مقایسه دو کالا'});await expect(dialog).toBeVisible()
 const headings=await dialog.locator('thead th').allTextContents();expect(headings.slice(1)).toEqual([titles[1],titles[0]])
})

test('ambiguous memory keeps exact cards and manual search clears continuation',async({page})=>{
 await page.goto('/');await page.getByLabel('نیاز شما').fill('گوشی A07');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.getByTestId('product-card').first()).toBeVisible();await expect(page.getByRole('button',{name:'توقف بررسی'})).toHaveCount(0)
 const original=await page.getByTestId('product-card').locator('h3').allTextContents()
 await page.getByLabel('نیاز شما').fill('همان مدل با حافظه بیشتر');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.locator('.ai-message')).toContainText('داخلی');await expect(page.locator('.ai-message')).toContainText('رم')
 expect(await page.getByTestId('product-card').locator('h3').allTextContents()).toEqual(original)
 await page.locator('.manual-search>summary').click();await page.getByLabel('جست‌وجوی کالا').fill('Lenovo');await page.getByRole('button',{name:'جست‌وجو',exact:true}).click()
 await expect(page.getByTestId('product-card').first()).toBeVisible()
 let parent:unknown='not-captured';page.on('request',r=>{if(new URL(r.url()).pathname==='/api/turns')parent=r.postDataJSON().discovery_parent_turn_id})
 await page.getByLabel('نیاز شما').fill('دومی را با اولی مقایسه کن');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.locator('.ai-message')).toContainText('ابتدا گزینه‌ها')
 expect(parent).toBeUndefined()
})

test('loading a sample clears the previous discovery parent instead of relabelling its cards',async({page})=>{
 await page.goto('/');await page.getByLabel('نیاز شما').fill('گوشی A07');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.getByTestId('product-card').first()).toBeVisible();await expect(page.getByRole('button',{name:'توقف بررسی'})).toHaveCount(0)
 await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await expect(page.getByTestId('simulation-banner')).toBeVisible()
 let parent:unknown='not-captured';page.on('request',r=>{if(new URL(r.url()).pathname==='/api/turns')parent=r.postDataJSON().discovery_parent_turn_id})
 await page.getByLabel('نیاز شما').fill('دومی را با اولی مقایسه کن');await page.getByRole('button',{name:'کمک برای انتخاب'}).click()
 await expect(page.locator('.ai-message')).toContainText('ابتدا گزینه‌ها');expect(parent).toBeUndefined()
 await expect(page.getByTestId('mission-product')).toContainText('64')
})


test('a late completed discovery cannot attach its parent to replacement sample cards',async({page})=>{
 let releaseTurn!:()=>void,releaseSample!:()=>void,arrivedTurn!:()=>void,arrivedSample!:()=>void
 const heldTurn=new Promise<void>(r=>{releaseTurn=r}),heldSample=new Promise<void>(r=>{releaseSample=r})
 const gotTurn=new Promise<void>(r=>{arrivedTurn=r}),gotSample=new Promise<void>(r=>{arrivedSample=r})
 let held=false
 await page.route('**/api/turns/*',async route=>{
  if(route.request().method()!=='GET'){await route.fallback();return}
  await reserveApiSlot();const response=await route.fetch();const result=await response.json()
  if(result.state==='completed'&&!held){held=true;arrivedTurn();await heldTurn}
  await route.fulfill({response})
 })
 await page.route('**/api/products/product_adfdc73bc839d15cd7754318',async route=>{arrivedSample();await heldSample;await route.fallback()})
 await page.goto('/');await page.getByLabel('نیاز شما').fill('گوشی A07');await page.getByRole('button',{name:'کمک برای انتخاب'}).click();await gotTurn
 await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click();await gotSample
 releaseTurn();await expect(page.locator('.discovery-context')).toHaveCount(0)
 releaseSample();await expect(page.getByTestId('simulation-banner')).toBeVisible();await expect(page.locator('.discovery-context')).toHaveCount(0)
})

test('accepting a newer manual diagnostic cancels and ignores an older completed AI result',async({page})=>{
 let release!:()=>void,arrived!:()=>void
 const held=new Promise<void>(r=>{release=r}),got=new Promise<void>(r=>{arrived=r})
 let heldOnce=false,canceled=false
 page.on('request',r=>{if(r.method()==='POST'&&/\/api\/turns\/[^/]+\/cancel$/.test(new URL(r.url()).pathname))canceled=true})
 await page.route('**/api/turns/*',async route=>{
  if(route.request().method()==='POST'){canceled=true;await route.fallback();return}
  await reserveApiSlot();const response=await route.fetch();const result=await response.json()
  if(result.state==='completed'&&!heldOnce){heldOnce=true;arrived();await held;result.result.products=[{product_id:'controlled-obsolete',title:'CONTROLLED obsolete discovery',brand:null,model:null,category:null,image_urls:[],specs:[],min_recorded_price:null}];await route.fulfill({response,json:result});return}
  await route.fulfill({response})
 })
 await page.goto('/');await expect(page.getByRole('button',{name:'کمک برای انتخاب'})).toBeEnabled()
 await page.locator('.manual-search>summary').click();await page.getByLabel('جست‌وجوی کالا').fill('A07');await page.getByLabel('بودجه به تومان').fill('1');await page.getByRole('button',{name:'جست‌وجو',exact:true}).click()
 await expect(page.getByRole('button',{name:'جست‌وجو با این بودجه'})).toBeVisible()
 await page.getByLabel('نیاز شما').fill('گوشی A07');await page.getByRole('button',{name:'کمک برای انتخاب'}).click();await got
 await page.getByRole('button',{name:'جست‌وجو با این بودجه'}).click();await expect(page.getByTestId('product-card').first()).toBeVisible()
 const current=await page.getByTestId('product-card').locator('h3').allTextContents()
 release();await expect(page.getByRole('button',{name:'توقف بررسی'})).toHaveCount(0);await page.waitForTimeout(1200)
 expect(await page.getByTestId('product-card').locator('h3').allTextContents()).toEqual(current)
 await expect(page.locator('.discovery-context')).toHaveCount(0);expect(canceled).toBe(true)
})
