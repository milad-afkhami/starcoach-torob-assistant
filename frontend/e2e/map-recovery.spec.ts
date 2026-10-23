import {test,expect} from './fixtures'
import type {Route,Page} from '@playwright/test'

// Valid deterministic image responses exercise real browser decoding and Leaflet
// tile events. These fixtures do not claim live OSM availability/geography.
const tile='<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#e8edf0"/><path d="M0 128H256M128 0V256" stroke="#fff" stroke-width="12"/></svg>'
const serve=(route:Route)=>route.fulfill({status:200,contentType:'image/svg+xml',body:tile})

async function sample(page:Page){
 await page.goto('/');await page.getByRole('button',{name:'دیدن سناریوی نمونه'}).click()
 await expect(page.locator('.shop-map .leaflet-marker-icon')).toHaveCount(2)
}

async function loadedCurrentTiles(page:Page){
 await expect.poll(()=>page.locator('.map-canvas img.leaflet-tile').evaluateAll(nodes=>{
  const tiles=nodes as HTMLImageElement[]
  const zoom=Math.max(...tiles.map(img=>Number(new URL(img.src).pathname.split('/')[1])))
  const current=tiles.filter(img=>Number(new URL(img.src).pathname.split('/')[1])===zoom)
  return current.length>0&&current.every(img=>img.complete&&img.naturalWidth>0)
 })).toBe(true)
}

test('late successful tile completion clears the timeout warning',async({page})=>{
 let release!:()=>void;const held=new Promise<void>(r=>{release=r})
 await page.route('https://tile.openstreetmap.org/**',async route=>{await held;await serve(route).catch(()=>{})})
 await sample(page)
 await expect(page.locator('.map-failure')).toBeVisible({timeout:9000})
 release();await loadedCurrentTiles(page)
 await expect(page.locator('.map-failure')).toHaveCount(0)
 await expect(page.locator('.map-loading')).toHaveCount(0)
 await expect(page.locator('.shop-map')).toContainText('OpenStreetMap')
})

test('a single loaded tile cannot hide inflight work or its bounded delay state',async({page})=>{
 let release!:()=>void;const held=new Promise<void>(r=>{release=r});const first=new Set<number>()
 await page.route('https://tile.openstreetmap.org/**',async route=>{
  const zoom=Number(new URL(route.request().url()).pathname.split('/')[1]);if(!first.has(zoom)){first.add(zoom);await serve(route);return}
  await held;await serve(route).catch(()=>{})
 })
 await sample(page)
 await expect(page.locator('.map-loading')).toBeVisible()
 await expect(page.locator('.map-failure')).toBeVisible({timeout:9000})
 release();await loadedCurrentTiles(page);await expect(page.locator('.map-failure')).toHaveCount(0)
})

test('real tile errors stay visible despite other successes and clear after a successful replacement view',async({page})=>{
 let failedURL:string|null=null,allowSuccess=false
 await page.route('https://tile.openstreetmap.org/**',async route=>{
  const zoom=Number(new URL(route.request().url()).pathname.split('/')[1])
  if(!allowSuccess&&zoom>=17&&!failedURL)failedURL=route.request().url()
  if(!allowSuccess&&route.request().url()===failedURL){await route.abort();return}
  await serve(route)
 })
 await sample(page);await expect(page.locator('.map-failure')).toBeVisible()
 expect(failedURL).not.toBeNull()
 await expect.poll(()=>page.locator('.map-canvas img.leaflet-tile').evaluateAll(nodes=>nodes.filter(node=>Number(new URL((node as HTMLImageElement).src).pathname.split('/')[1])>=17&&(node as HTMLImageElement).naturalWidth>0).length)).toBeGreaterThan(0)
 await expect(page.locator('.map-failure')).toBeVisible()
 allowSuccess=true;await page.locator('.leaflet-control-zoom-in').click()
 await loadedCurrentTiles(page);await expect(page.locator('.map-failure')).toHaveCount(0)
 await expect(page.locator('.map-shop-list button')).toHaveCount(2)
})

test('failed empty tiles and late responses after unmount never report a successful map',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
 await page.route('https://tile.openstreetmap.org/**',route=>route.abort())
 await sample(page);await expect(page.locator('.map-failure')).toBeVisible()
 expect(await page.locator('.map-canvas img.leaflet-tile').evaluateAll(nodes=>nodes.some(node=>(node as HTMLImageElement).naturalWidth>0))).toBe(false)
 await page.unroute('https://tile.openstreetmap.org/**')
 let release!:()=>void;const held=new Promise<void>(r=>{release=r});let immediate=false
 await page.route('https://tile.openstreetmap.org/**',async route=>{if(!immediate)await held;await serve(route).catch(()=>{})})
 await page.getByRole('button',{name:'گفت‌وگوی تازه'}).click();await sample(page)
 await expect(page.locator('.map-loading')).toBeVisible()
 await page.getByRole('button',{name:'گفت‌وگوی تازه'}).click();immediate=true;release()
 await expect(page.locator('.shop-map')).toHaveCount(0)
 await sample(page);await loadedCurrentTiles(page)
 await expect(page.locator('.map-loading,.map-failure')).toHaveCount(0)
 expect(errors).toEqual([])
})
