import assert from 'node:assert/strict'
import {test} from 'node:test'
import {comparisonRows} from './comparison.ts'
import type {Product} from './types.ts'
const product=(specs:Product['specs'])=>({product_id:'p',specs} as Product)

test('RAM and storage aliases align only compatible unit families and retain source labels',()=>{
 const rows=comparisonRows([
  product([{key:'حافظه RAM',section:'حافظه',value:'۶ گیگابایت'},{key:'ظرفیت حافظه داخلی',value:'۱۲۸ گیگابایت'}]),
  product([{key:'ظرفیت رم',section:'مشخصات کلی',value:'8 GB'},{key:'حافظه داخلی',value:'256 GB'}]),
 ])
 const ram=rows.find(r=>r.label==='حافظه رم')!;assert.deepEqual(ram.values,['۶ گیگابایت','8 GB']);assert.deepEqual(ram.sourceLabels,[['حافظه RAM'],['ظرفیت رم']])
 assert.equal(rows.length,2);assert.deepEqual(rows.find(r=>r.label==='حافظه داخلی')!.values,['۱۲۸ گیگابایت','256 GB'])
})

test('RAM type, different units and absent values never become inferred capacities',()=>{
 const rows=comparisonRows([
  product([{key:'ظرفیت رم',value:'6 GB'},{key:'نوع رم',value:'LPDDR4'},{key:'سیستم عامل',value:'Android'}]),
  product([{key:'حافظه RAM',value:'8192 MB'},{key:'نوع رم',value:'LPDDR5'},{key:'نسخه سیستم عامل',value:'15'}]),
 ])
 const ram=rows.filter(r=>r.label==='حافظه رم');assert.equal(ram.length,2)
 assert.deepEqual(ram.map(r=>r.values),[['6 GB',null],[null,'8192 MB']])
 assert.equal(rows.filter(r=>r.label.includes('سیستم عامل')).length,2)
})

test('capacity units attached to numbers align with their full Persian spelling',()=>{
 const rows=comparisonRows([product([{key:'حافظه RAM',value:'6GB'}]),product([{key:'ظرفیت رم',value:'۸ گیگابایت'}])])
 assert.equal(rows.length,1);assert.deepEqual(rows[0].values,['6GB','۸ گیگابایت'])
})
