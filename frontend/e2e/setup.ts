import {request,type FullConfig} from '@playwright/test'
import {mkdirSync,chmodSync} from 'node:fs'
import {dirname} from 'node:path'
import {fileURLToPath} from 'node:url'

/** Independent fixture users keep unrelated suites below each user's real request limit.
 * No limiter, state database or model budget is reset or raised. Cookies remain private.
 */
export default async function setup(config:FullConfig){
 const origin=String(config.projects[0].use.baseURL)
 for(const suffix of ['', '-conversation', '-discovery']){
  const client=await request.newContext({baseURL:origin,extraHTTPHeaders:{Origin:origin}})
  try{
   const response=await client.post('/api/sessions')
   if(!response.ok())throw new Error(`Actual session setup failed: HTTP ${response.status()}`)
   const path=fileURLToPath(new URL(`../../data/ui-test-session${suffix}.json`,import.meta.url));mkdirSync(dirname(path),{recursive:true})
   await client.storageState({path});chmodSync(path,0o600)
  }finally{await client.dispose()}
 }
}
