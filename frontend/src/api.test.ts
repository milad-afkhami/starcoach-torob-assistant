import test from 'node:test'
import assert from 'node:assert/strict'
import * as apiModule from './api.ts'

const originalFetch=globalThis.fetch
test.afterEach(()=>{globalThis.fetch=originalFetch})
type ReaderFactory=(id:string,deadline:number,active:()=>boolean,options?:{now:()=>number;wait:(ms:number)=>Promise<void>})=><T>()=>Promise<T|null>
function readerFactory(){const factory=(apiModule as unknown as {createTurnReader:ReaderFactory}).createTurnReader;assert.equal(typeof factory,'function');return factory}

 test('transient owned-turn reads recover the same completed observation without replaying POST',async()=>{
 const calls:{path:string;method:string}[]=[];let gets=0,now=0
 globalThis.fetch=async(input,init)=>{calls.push({path:String(input),method:init?.method||'GET'});if(init?.method==='POST')return Response.json({id:'owned-turn'});if(++gets===1)throw new TypeError('network lost');return Response.json({state:'completed',result:{observation:{id:'same-preview'}}})}
 await apiModule.api.post('/api/turns',{kind:'reply'})
 const read=readerFactory()('owned-turn',120000,()=>true,{now:()=>now,wait:async ms=>{now+=ms}})
 assert.equal((await read<{result:{observation:{id:string}}}>())?.result.observation.id,'same-preview')
 assert.equal(calls.filter(x=>x.method==='POST').length,1)
 assert.deepEqual(calls.filter(x=>x.method==='GET').map(x=>x.path),['/api/turns/owned-turn','/api/turns/owned-turn'])
})

test('persistent transport loss consumes at most three retries across the complete turn',async()=>{
 let gets=0,now=0;globalThis.fetch=async()=>{if(++gets===2)return Response.json({state:'running'});throw new TypeError('network lost')}
 const read=readerFactory()('owned-turn',120000,()=>true,{now:()=>now,wait:async ms=>{now+=ms}})
 assert.deepEqual(await read(),{state:'running'})
 await assert.rejects(read(),error=>error instanceof Error&&error.name==='TransportError')
 assert.equal(gets,5) // Two successful read cycles, only three failed-read retries shared across both.
})

test('cancellation during retry wait cannot fetch or resurrect the completed turn',async()=>{
 let gets=0,current=true;globalThis.fetch=async()=>{gets++;throw new TypeError('network lost')}
 const read=readerFactory()('owned-turn',120000,()=>current,{now:()=>0,wait:async()=>{current=false}})
 assert.equal(await read(),null);assert.equal(gets,1)
})

test('original monotonic deadline prevents retry after backoff or a late completed response',async()=>{
 let gets=0,now=0;globalThis.fetch=async()=>{gets++;throw new TypeError('network lost')}
 const read=readerFactory()('owned-turn',100,()=>true,{now:()=>now,wait:async ms=>{now+=ms}})
 await assert.rejects(read());assert.equal(gets,1)
 globalThis.fetch=async()=>{now=200;return Response.json({state:'completed'})};now=0
 await assert.rejects(readerFactory()('owned-turn',100,()=>true,{now:()=>now,wait:async()=>{}})())
})

for(const status of [401,403,404,409,429,500,501])test(`HTTP ${status} is never silently retried`,async()=>{
 let gets=0;globalThis.fetch=async()=>{gets++;return Response.json({detail:'controlled'},{status})}
 const read=readerFactory()('owned-turn',120000,()=>true,{now:()=>0,wait:async()=>{}})
 await assert.rejects(read());assert.equal(gets,1)
})
for(const status of [502,503,504])test(`HTTP ${status} permits bounded same-turn read recovery`,async()=>{
 let gets=0;globalThis.fetch=async()=>++gets===1?Response.json({detail:'controlled'},{status}):Response.json({state:'completed'})
 const read=readerFactory()('owned-turn',120000,()=>true,{now:()=>0,wait:async()=>{}})
 assert.deepEqual(await read(),{state:'completed'});assert.equal(gets,2)
})
test('failed mutation remains single attempt and has a precise transport error',async()=>{
 let calls=0;globalThis.fetch=async()=>{calls++;throw new TypeError('network lost')}
 await assert.rejects(apiModule.api.post('/api/turns',{kind:'reply'}),error=>error instanceof Error&&error.name==='TransportError')
 assert.equal(calls,1)
})

test('a hanging owned-turn GET is aborted at the original deadline without a retry',async()=>{
 let gets=0,aborted=false
 globalThis.fetch=async(_input,init)=>{gets++;return new Promise<Response>((_resolve,reject)=>{assert.ok(init?.signal);init.signal.addEventListener('abort',()=>{aborted=true;reject(new TypeError('controlled fetch aborted'))},{once:true})})}
 const read=readerFactory()('owned-turn',performance.now()+100,()=>true)
 await assert.rejects(read(),error=>error instanceof apiModule.ApiError&&error.status===408)
 assert.equal(aborted,true);assert.equal(gets,1)
})
