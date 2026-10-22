import {request,type FullConfig} from '@playwright/test'
import {mkdirSync,chmodSync} from 'node:fs'
import {dirname} from 'node:path'
import {fileURLToPath} from 'node:url'

/** Exercise one real anonymous sign-in, then reuse that owner's cookie in isolated contexts.
 * This avoids accidentally load-testing the new-owner throttle in a sequential UI suite.
 * Cross-owner isolation remains covered by independent API tests.
 */
export default async function setup(config:FullConfig){
 const origin=String(config.projects[0].use.baseURL)
 const client=await request.newContext({baseURL:origin,extraHTTPHeaders:{Origin:origin}})
 try{
  const response=await client.post('/api/sessions')
  if(!response.ok())throw new Error(`Actual session setup failed: HTTP ${response.status()}`)
  const path=fileURLToPath(new URL('../../data/ui-test-session.json',import.meta.url));mkdirSync(dirname(path),{recursive:true})
  await client.storageState({path});chmodSync(path,0o600)
 }finally{await client.dispose()}
}
