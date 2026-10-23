import {useEffect,useState} from 'react'
import {X,LoaderCircle} from 'lucide-react'
import {api} from './api'
import {comparisonRows} from './comparison'
import {Dialog} from './Dialog'
import {faDate,formatToman,localInput} from './format'
import {reasonLabels} from './SellerCard'
import type {Constraints,Product,ProductFeasibility} from './types'

export function ProductComparison({products,constraints,onClose,onSelect,inline=false,disabledIds=[]}:{products:Product[];constraints:Constraints;onClose:()=>void;onSelect:(p:Product)=>void;inline?:boolean;disabledIds?:string[]}){
 const [items,setItems]=useState<ProductFeasibility[]|null>(null),[state,setState]=useState<'loading'|'ready'|'failed'>('loading'),[error,setError]=useState(''),[allSpecs,setAllSpecs]=useState(false),[attempt,setAttempt]=useState(0)
 useEffect(()=>{
  let alive=true;setState('loading');setError('');setItems(null)
  void api.post<{products:ProductFeasibility[]}>('/api/products/compare',{product_ids:products.map(p=>p.product_id),constraints}).then(r=>{
   if(!Array.isArray(r.products)||r.products.length!==products.length||r.products.some((p,i)=>p.product.product_id!==products[i].product_id))throw new Error('پاسخ مقایسه کامل نبود؛ دوباره بررسی کن.')
   if(alive){setItems(r.products);setState('ready')}
  }).catch(e=>{if(alive){setError(e instanceof Error?e.message:'بررسی انجام نشد.');setState('failed')}})
  return()=>{alive=false}
 },[attempt])
 const rows=comparisonRows(products),pending=state==='failed'?'بررسی انجام نشد؛ نامشخص':'در حال بررسی'
 function derived(i:number,render:(item:ProductFeasibility)=>string){return state==='ready'&&items?render(items[i]):pending}
 const Wrapper=inline?'section':Dialog
 return <Wrapper className={inline?"inline-comparison":"comparison-modal"} label="مقایسه دو کالا" onClose={onClose}>
  <div className="section-heading"><h2>کدام گزینه برای خرید تو عملی‌تر است؟</h2>{!inline&&<button className="icon-button" aria-label="بستن مقایسه" onClick={onClose}><X/></button>}</div>
  <p className="comparison-context">همان شرایط فرم: بودجه {constraints.max_price_toman?formatToman(constraints.max_price_toman)+' تومان':'بدون سقف'}، شعاع {new Intl.NumberFormat('fa-IR').format(constraints.radius_km)} کیلومتر، مبدأ {constraints.origin_label||'نقطه انتخاب‌شده'} (<bdi>{constraints.lat.toFixed(4)}, {constraints.lon.toFixed(4)}</bdi>)، مراجعه {faDate(constraints.visit_at)} {constraints.visit_at?`ساعت ${localInput(constraints.visit_at).slice(11)} تهران`:''}. {constraints.payment_provider&&`پرداخت ${constraints.payment_provider}. `}{constraints.contactable_only&&'فقط فروشگاه با مسیر تماس ثبت‌شده.'}</p>
  {state==='failed'&&<div className="notice error"><p role="alert">{error} نتیجه امکان خرید نامشخص است؛ خطا به معنی نبود فروشنده نیست.</p><button className="button soft-button" onClick={()=>setAttempt(x=>x+1)}>تلاش دوباره برای مقایسه</button></div>}
  {state==='loading'&&<p role="status"><LoaderCircle size={16} className="spin"/>در حال بررسی امکان مراجعه…</p>}
  <div className="comparison-scroll"><table className="comparison-table"><caption className="sr-only">مقایسه مشخصات ثبت‌شده و امکان خرید در شرایط انتخابی</caption>
   <thead><tr><th scope="col">معیار</th>{products.map(p=><th key={p.product_id} scope="col">{p.title||'عنوان ثبت نشده'}</th>)}</tr></thead>
   <tbody>
    <tr><th scope="row">کمترین قیمت کل داده</th>{products.map((p,i)=><td key={p.product_id}>{derived(i,item=>item.product.min_recorded_price===null?'قیمت ثبت نشده':`${formatToman(item.product.min_recorded_price)} تومان`)}</td>)}</tr>
    <tr><th scope="row">فروشگاه سازگار در محدوده</th>{products.map((p,i)=><td key={p.product_id}>{derived(i,item=>`${new Intl.NumberFormat('fa-IR').format(item.eligible_shops)} از ${new Intl.NumberFormat('fa-IR').format(item.distinct_shops)} فروشگاه`)}</td>)}</tr>
    <tr><th scope="row">قیمت گزینه سازگار</th>{products.map((p,i)=><td key={p.product_id}>{derived(i,item=>item.best_offer?`${formatToman(item.best_offer.price_toman)} تومان`:'گزینه سازگار ثبت نشده')}</td>)}</tr>
    <tr><th scope="row">فاصله مستقیم گزینه اول</th>{products.map((p,i)=><td key={p.product_id}>{derived(i,item=>item.best_offer?.straight_line_km!=null?`${new Intl.NumberFormat('fa-IR',{maximumFractionDigits:2}).format(item.best_offer.straight_line_km)} کیلومتر`:'نامشخص')}</td>)}</tr>
    <tr><th scope="row">موانع ثبت‌شده</th>{products.map((p,i)=><td key={p.product_id}>{derived(i,item=>Object.keys(item.exclusion_reasons).map(r=>reasonLabels[r]||'نیازمند بررسی').join('، ')||'مانع ثبت‌شده ندارد؛ استعلام لازم است')}</td>)}</tr>
    {rows.slice(0,allSpecs?undefined:12).map(row=><tr key={row.id}><th scope="row">{row.label}</th>{row.values.map((value,i)=><td key={products[i].product_id}>{value||'در داده ثبت نشده'}{value&&row.sourceLabels[i].length>0&&<small className="comparison-source-label">عنوان منبع: {row.sourceLabels[i].join('، ')}</small>}</td>)}</tr>)}
    {rows.length===0&&<tr><th scope="row">مشخصات فنی</th>{products.map(p=><td key={p.product_id}>در داده ثبت نشده؛ از عنوان مدل قابلیت حدس نمی‌زنیم</td>)}</tr>}
    <tr><th scope="row">موجودی</th>{products.map(p=><td key={p.product_id}>نامشخص؛ نیازمند استعلام</td>)}</tr>
    <tr><th scope="row">انتخاب شما</th>{products.map(p=><td key={p.product_id}><button className="button primary-button" disabled={disabledIds.includes(p.product_id)} onClick={()=>onSelect(p)}>{disabledIds.includes(p.product_id)?'شرط‌های بررسی‌نشده مانع انتخاب‌اند':'انتخاب این کالا'}</button></td>)}</tr>
   </tbody>
  </table></div>
  {rows.length>12&&<button className="button soft-button" onClick={()=>setAllSpecs(x=>!x)}>{allSpecs?'فقط مشخصات کلیدی':'نمایش همه مشخصات ثبت‌شده'}</button>}
  <p className="source-note">مقایسه از کاتالوگ است و گزارش‌های خصوصی برنامه را وارد نمی‌کند. سازگاری بر اساس قیمت تاریخی، موقعیت و ساعت اعلام‌شده است؛ تضمین موجودی، اصالت یا کیفیت نیست. نام‌های هم‌معنی محدود با واحد یکسان کنار هم‌اند؛ مقدارها و عنوان منبع حفظ شده‌اند. نبود مشخصه به معنی نداشتن آن قابلیت نیست.</p>
 </Wrapper>
}
