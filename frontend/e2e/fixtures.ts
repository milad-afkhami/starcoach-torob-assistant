import {test as base,expect,type APIRequestContext} from '@playwright/test'
import {fileURLToPath} from 'node:url'

// Functional journeys are not an anonymous-IP load test. The public API allows
// 180 requests/minute; pace this single worker below that boundary, without
// changing/resetting the server limiter or replaying any rejected mutation.
let nextApiSlot=0
export async function reserveApiSlot(){
 const slot=Math.max(Date.now(),nextApiSlot);nextApiSlot=slot+400
 const wait=slot-Date.now();if(wait>0)await new Promise(resolve=>setTimeout(resolve,wait))
}
export async function apiGet(client:APIRequestContext,...args:Parameters<APIRequestContext['get']>){await reserveApiSlot();return client.get(...args)}
export async function apiPatch(client:APIRequestContext,...args:Parameters<APIRequestContext['patch']>){await reserveApiSlot();return client.patch(...args)}
export const test=base.extend<{apiPacing:void}>({
 storageState:async({},use,testInfo)=>{
  const suffix=testInfo.file.endsWith('/conversation.spec.ts')?'-conversation':testInfo.file.endsWith('/discovery-context.spec.ts')?'-discovery':''
  await use(fileURLToPath(new URL(`../../data/ui-test-session${suffix}.json`,import.meta.url)))
 },
 apiPacing:[async({page},use)=>{
  await page.route('**/api/**',async route=>{
   await reserveApiSlot()
   await route.continue()
  })
  await use()
 },{auto:true}],
})
export {expect}
