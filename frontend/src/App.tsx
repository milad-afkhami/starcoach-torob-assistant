import { useEffect, useRef, useState } from 'react'
import { Search, Sparkles, ShoppingBag, MapPin, Navigation, RefreshCcw, X, Copy, ExternalLink, Check, LoaderCircle, ArrowLeft, SlidersHorizontal } from 'lucide-react'
import { api, ApiError, errorText } from './api'
import { faDate, formatToman, localInput, normalizeDigits, parseToman, visitIso } from './format'
import { SellerCard, outcomeLabels, reasonLabels } from './SellerCard'
import type { Constraints, Delta, ExternalAction, Followup, Mission, MissionResponse, Observation, Plan, Product, Recommendation, SearchDiagnostic, Turn } from './types'
import './style.css'
import { Dialog } from './Dialog'
import { Select } from './Select'
import { LocationChooser } from './LocationChooser'
import { ProductComparison } from './ProductComparison'

type Draft = {query:string;category:string;budget:string;lat:string;lon:string;radius:string;visit:string;payment:string;open:boolean;contactable:boolean;originLabel:string}
const tradeoffLabels:Record<string,string>={cheapest:'کمترین قیمت',closest:'نزدیک‌ترین',nearby_alternatives:'جایگزین‌های نزدیک'}
const FIXTURE='product_adfdc73bc839d15cd7754318'
const DEMO:Constraints={query:'A07',category:'گوشی موبایل',max_price_toman:'40000000',lat:35.69508821734553,lon:51.41148102579503,radius_km:1,payment_provider:null,visit_at:'2026-10-22T20:15:00+03:30',require_declared_open:true,origin_label:'محدوده جمهوری (نقطه پیش‌فرض)'}
function draftOf(c:Constraints):Draft{return {query:c.query,category:c.category||'',budget:c.max_price_toman||'',lat:String(c.lat),lon:String(c.lon),radius:String(c.radius_km),visit:c.visit_at?localInput(c.visit_at):localInput(new Date()).slice(0,10)+'T17:00',payment:c.payment_provider||'',open:c.require_declared_open,contactable:!!c.contactable_only,originLabel:c.origin_label||''}}
function readDraft(d:Draft):Constraints{
  const lat=Number(normalizeDigits(d.lat)),lon=Number(normalizeDigits(d.lon)),radius=Number(normalizeDigits(d.radius))
  if(!d.lat.trim()||!d.lon.trim()||!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)throw new Error('مختصات معتبر وارد کنید یا محدوده جمهوری را انتخاب کنید.')
  if(!Number.isFinite(radius)||radius<=0||radius>50)throw new Error('شعاع جست‌وجو باید بیشتر از صفر و حداکثر پنجاه کیلومتر باشد.')
  return {query:d.query,category:d.category||null,max_price_toman:parseToman(d.budget),lat,lon,radius_km:radius,payment_provider:d.payment||null,visit_at:visitIso(d.visit),require_declared_open:d.open,contactable_only:d.contactable,origin_label:d.originLabel||null}
}
const shortError=(error:unknown)=>error instanceof Error?error.message:'درخواست انجام نشد؛ دوباره تلاش کنید.'
const sleep=(ms:number)=>new Promise(resolve=>setTimeout(resolve,ms))
function editConditions(){const section=document.querySelector<HTMLDetailsElement>('.manual-search');if(section){section.open=true;section.scrollIntoView({behavior:'smooth',block:'start'});section.querySelector<HTMLInputElement>('input[inputmode="numeric"]')?.focus({preventScroll:true})}}
function scrollMission(){const node=document.getElementById('mission');node?.focus({preventScroll:true});node?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'})}

function ExcludedSellers({options,onFollowup,busy}:{options:Plan['excluded'];onFollowup:(id:string)=>void;busy:boolean}){
 const groups=new Map<string,typeof options>()
 for(const option of options){const reason=option.reason_codes.find(x=>x.startsWith('reported_')||x==='no_response'||x==='variant_mismatch')||option.reason_codes[0]||'unknown';groups.set(reason,[...(groups.get(reason)||[]),option])}
 return <>{[...groups].sort(([,a],[,b])=>Number(b.some(x=>x.offer.observations.length>0))-Number(a.some(x=>x.offer.observations.length>0))).map(([reason,items])=><details className="excluded-group" key={reason} open={items.some(x=>x.offer.observations.length>0)}><summary>{reasonLabels[reason]||'نیازمند بررسی'}<span>{items.length} پیشنهاد</span></summary>{items.map(o=><SellerCard key={o.offer.offer_id} option={o} role="excluded" compact disabled={busy} onFollowup={onFollowup}/>)}</details>)}</>
}

function ProductCard({product,recommendation,compared,onCompare,onSelect,busy}:{product:Product;recommendation?:Recommendation;compared:boolean;busy:boolean;onCompare:()=>void;onSelect:()=>void}){
  return <article className="product-card" data-testid="product-card">
    <div className="product-image"><ShoppingBag size={38} aria-hidden="true"/>{product.image_urls[0]&&<img src={product.image_urls[0]} alt={product.title||'تصویر کالای داده'} loading="lazy" referrerPolicy="no-referrer" onError={e=>{e.currentTarget.style.display='none'}}/>}</div>
    <div className="product-body"><span className="category-label">{product.category||'دسته‌بندی ثبت نشده'}</span><h3>{product.title||'عنوان کالا ثبت نشده'}</h3>
      <p className="product-price"><bdi>{formatToman(product.min_recorded_price)}</bdi>{product.min_recorded_price!==null&&<small>تومان</small>}</p><p className="source-note">قیمت ثبت‌شده؛ موجودی نامشخص</p>
      {recommendation&&<details className="recommendation"><summary><Sparkles size={13}/>چرا این گزینه؟</summary><p>{recommendation.reason_fa}</p>{recommendation.facts.map(f=><p key={f.id}><b>{f.label}: </b>{f.id.endsWith(':price')?formatToman(f.value)+' تومان':f.value}</p>)}</details>}
      <div className="product-actions"><button className="button soft-button" disabled={busy} onClick={onSelect}>انتخاب این کالا<ArrowLeft size={15}/></button><label className="compare-check"><input type="checkbox" checked={compared} onChange={onCompare}/>مقایسه</label></div>
    </div>
  </article>
}

export default function App(){
  const [draft,setDraft]=useState<Draft>(()=>draftOf({...DEMO,query:'',category:null,max_price_toman:null,require_declared_open:true,visit_at:localInput(new Date()).slice(0,10)+'T17:00:00+03:30'}))
  const [products,setProducts]=useState<Product[]>([]),[recommendations,setRecommendations]=useState<Recommendation[]>([])
  const [compared,setCompared]=useState<Product[]>([]),[showCompare,setShowCompare]=useState(false),[compareConstraints,setCompareConstraints]=useState<Constraints|null>(null)
  const [locationOpen,setLocationOpen]=useState(false),[searchDiagnostics,setSearchDiagnostics]=useState<SearchDiagnostic[]>([])
  const [initKey,setInitKey]=useState(0),[initFailed,setInitFailed]=useState(false),[staleMissionId,setStaleMissionId]=useState<string|null>(null)
  const [mission,setMission]=useState<Mission|null>(null),[plan,setPlan]=useState<Plan|null>(null),[product,setProduct]=useState<Product|null>(null)
  const [ready,setReady]=useState(false),[modelAvailable,setModelAvailable]=useState(false),[busy,setBusy]=useState(false),[searched,setSearched]=useState(false)
  const [error,setError]=useState(''),[toast,setToast]=useState(''),[delta,setDelta]=useState<Delta|null>(null),[history,setHistory]=useState<Delta[]>([])
  const [actions,setActions]=useState<ExternalAction[]>([]),[transportOpen,setTransportOpen]=useState(false)
  const [revealTick,setRevealTick]=useState(0)
  const revealOrigin=useRef<Element|null>(null)
  const [userNeed,setUserNeed]=useState('')
  const [discoveryParent,setDiscoveryParent]=useState<string|null>(null),[comparisonSuggestion,setComparisonSuggestion]=useState<{products:Product[];constraints:Constraints}|null>(null)
  const [need,setNeed]=useState(''),[aiScope,setAiScope]=useState<'discovery'|'mission'>('discovery'),[turn,setTurn]=useState<Turn|null>(null)
  const [aiMessage,setAiMessage]=useState(''),[proposal,setProposal]=useState<{constraints:Constraints;missionId:string|null;baseRevision:number|null;summary?:number}|null>(null)
  const [followup,setFollowup]=useState<(Followup&{missionId:string;baseRevision:number})|null>(null),[replyText,setReplyText]=useState('')
  const [outcome,setOutcome]=useState('unavailable'),[quote,setQuote]=useState(''),[closureDate,setClosureDate]=useState(()=>localInput(new Date()).slice(0,10)),[preview,setPreview]=useState<Observation|null>(null)
  const [aiPending,setAiPending]=useState(false)
  const interactionEpoch=useRef(0)
  const aiEpoch=useRef(0),replyTrigger=useRef<HTMLElement|null>(null)
  const activeTurn=useRef<string|null>(null),missionRef=useRef<Mission|null>(null)
  missionRef.current=mission

  function revealFrom(origin:Element|null){revealOrigin.current=origin;setRevealTick(t=>t+1)}
  function revealMission(){revealFrom(document.activeElement)}
  useEffect(()=>{if(!revealTick)return;const frame=requestAnimationFrame(()=>{const active=document.activeElement;if(active===revealOrigin.current||active===replyTrigger.current||active===document.body)scrollMission()});return()=>cancelAnimationFrame(frame)},[revealTick])

  function updateDraft<K extends keyof Draft>(key:K,value:Draft[K]){interactionEpoch.current++;setDraft(d=>({...d,[key]:value,...(key==='lat'||key==='lon'?{originLabel:''}:{})}))}
  function accept(response:MissionResponse,selected?:Product){
    setMission(response.mission);setPlan(response.plan);setStaleMissionId(null)
    if(selected||response.product)setProduct(selected||response.product!)
    try{localStorage.setItem('plan-b:last-mission',response.mission.id)}catch{/* Browser storage may be unavailable; server state is still private. */}
  }
  async function cancelAI(silent=false){
    aiEpoch.current++;setAiPending(false);const id=activeTurn.current;activeTurn.current=null;setTurn(null)
    if(!silent)setAiMessage('بررسی متوقف شد. برنامه تغییری نکرد.')
    if(id)await api.post(`/api/turns/${id}/cancel`).catch(()=>undefined)
  }
  useEffect(()=>{
    let alive=true
    async function init(){
      const epoch=interactionEpoch.current
      setInitFailed(false)
      try{
        await api.post('/api/sessions')
        const cap=await api.get<{catalogue_ready:boolean;model_available:boolean}>('/api/capabilities')
        if(!alive)return
        setReady(cap.catalogue_ready);setModelAvailable(cap.model_available)
        let saved:string|null=null;try{saved=localStorage.getItem('plan-b:last-mission')}catch{/* optional browser storage */}
        if(saved){try{const r=await api.get<MissionResponse>(`/api/missions/${saved}`);if(alive&&interactionEpoch.current===epoch){accept(r);setDraft(draftOf(r.mission.constraints))}}catch(e){if(e instanceof Error&&e.message===errorText('not_found')){try{if(interactionEpoch.current===epoch&&localStorage.getItem('plan-b:last-mission')===saved)localStorage.removeItem('plan-b:last-mission')}catch{/* optional */}}else throw e}}
      }catch(e){if(alive){setError(shortError(e));setInitFailed(true)}}
    }
    void init()
    const timer=setInterval(()=>{void api.get<{model_available:boolean}>('/api/capabilities').then(x=>{if(alive)setModelAvailable(x.model_available)}).catch(()=>{if(alive)setModelAvailable(false)})},15000)
    return()=>{alive=false;clearInterval(timer);activeTurn.current=null}
  },[initKey])
  useEffect(()=>{
    let alive=true;setActions([])
    if(mission){
      void api.get<{revision:number;actions:ExternalAction[]}>(`/api/missions/${mission.id}/actions`).then(r=>{if(alive&&r.revision===mission.revision)setActions(r.actions)}).catch(()=>undefined)
      void api.get<{events:Delta[]}>(`/api/missions/${mission.id}/history`).then(r=>{if(alive)setHistory(r.events)}).catch(()=>undefined)
    }
    return()=>{alive=false}
  },[mission?.id,mission?.revision])

  async function manualSearch(event?:React.FormEvent){
    event?.preventDefault();setDiscoveryParent(null);setComparisonSuggestion(null);setError('');setBusy(true);await cancelAI(true)
    try{const c=readDraft(draft);const r=await api.post<{products:Product[];diagnostics:SearchDiagnostic[]}>('/api/search',c);setProducts(r.products);setSearchDiagnostics(r.diagnostics||[]);setRecommendations([]);setSearched(true);setAiMessage('');setProposal(null)}catch(e){setError(shortError(e))}finally{setBusy(false)}
  }
  async function selectProduct(p:Product,c?:Constraints,mode:'assisted'|'simulation'='assisted',origin:Element|null=document.activeElement){
    interactionEpoch.current++
    setError('');setBusy(true);await cancelAI(true)
    try{const r=await api.post<MissionResponse>('/api/missions',{product_id:p.product_id,constraints:c||readDraft(draft),mode});accept(r,p);setDelta(null);setFollowup(null);setPreview(null);setTransportOpen(false);setToast('کالا انتخاب شد؛ حالا شرایط مراجعه و گزینه دوم را بررسی کنید.');revealFrom(origin)}catch(e){setError(shortError(e))}finally{setBusy(false)}
  }
  async function loadDemo(){
    setDiscoveryParent(null);setComparisonSuggestion(null)
    const origin=document.activeElement
    const editEpoch=++interactionEpoch.current
    setError('');setBusy(true);setSearchDiagnostics([]);await cancelAI(true)
    try{const p=await api.get<Product>(`/api/products/${FIXTURE}`);if(interactionEpoch.current===editEpoch)setDraft(draftOf(DEMO));setDiscoveryParent(null);setComparisonSuggestion(null);setProducts([p]);setSearched(true);setRecommendations([]);await selectProduct(p,DEMO,'simulation',origin)}catch(e){setError(shortError(e));setBusy(false)}
  }
  async function applyConditions(c?:Constraints,expected?:number){
    if(!mission||staleMissionId)return
    const editEpoch=interactionEpoch.current
    setError('');setBusy(true);await cancelAI(true)
    try{const conditions=c||readDraft(draft);const r=await api.patch<MissionResponse>(`/api/missions/${mission.id}`,{expected_revision:expected??mission.revision,constraints:conditions});accept(r);const untouched=interactionEpoch.current===editEpoch;if(untouched)setDraft(draftOf(r.mission.constraints));setFollowup(null);setPreview(null);setDelta(null);setProposal(null);setToast(untouched?'شرایط با انتخاب شما تغییر کرد؛ برنامه دوباره محاسبه شد.':'برنامه ذخیره شد؛ ویرایش تازه فرم هنوز اعمال نشده است.')}catch(e){setError(shortError(e));if(e instanceof ApiError&&e.code==='stale_revision')setStaleMissionId(mission.id)}finally{setBusy(false)}
  }
  async function refreshMission(){
    const id=staleMissionId;if(!id)return
    setBusy(true);setError('')
    try{const r=await api.get<MissionResponse>(`/api/missions/${id}`);if(missionRef.current?.id!==id||r.mission.revision<missionRef.current.revision)return;accept(r);setProposal(null);setFollowup(null);setPreview(null);setDelta(null);setToast('برنامه تازه شد؛ ویرایش‌های فرم حفظ شدند. پیشنهاد تازه هنوز اعمال نشده است.')}
    catch(e){setError(shortError(e))}finally{setBusy(false)}
  }
  async function applyProposal(){
    if(!proposal)return
    if(proposal.missionId){if(mission?.id!==proposal.missionId){setError('این پیشنهاد برای برنامه دیگری است.');return}await applyConditions(proposal.constraints,proposal.baseRevision!)}
    else{setDraft(draftOf(proposal.constraints));setToast('پیشنهاد در فرم قرار گرفت؛ برای انتخاب کالا یا تغییر برنامه، دکمه مربوط را بزنید.');setProposal(null)}
  }
  async function startAI(kind:'needs'|'reply'){
    setError('');await cancelAI(true)
    const epoch=aiEpoch.current;setAiPending(true)
    const target=kind==='reply'?followup:aiScope==='mission'&&mission?{missionId:mission.id,baseRevision:mission.revision}:null
    try{
      const message=kind==='reply'?replyText:need
      if(!message.trim())throw new Error('ابتدا متن درخواست یا پاسخ را بنویسید.')
      if(kind==='needs')setUserNeed(message)
      const body={kind,message,mission_id:target?.missionId||null,base_revision:target?.baseRevision||null,followup_id:kind==='reply'?followup?.id:null,constraints:readDraft(draft),...(kind==='needs'&&!target&&discoveryParent?{discovery_parent_turn_id:discoveryParent}:{})}
      let state=await api.post<Turn>('/api/turns',body);if(aiEpoch.current!==epoch){void api.post(`/api/turns/${state.id}/cancel`).catch(()=>undefined);return}setAiPending(false);activeTurn.current=state.id;setTurn(state);setAiMessage('');setProposal(null)
      const id=state.id
      while(['running','advancing'].includes(state.state)&&activeTurn.current===id){await sleep(1000);if(activeTurn.current!==id)return;state=await api.get<Turn>(`/api/turns/${id}`);if(activeTurn.current!==id)return;setTurn(state)}
      if(activeTurn.current!==id)return
      activeTurn.current=null;setTurn(null)
      if(state.state!=='completed'){setAiMessage(errorText(state.error_code));if(kind==='needs'){setDiscoveryParent(null);setComparisonSuggestion(null)}if(state.result?.products.length)setProducts(state.result.products);return}
      const r=state.result!
      if(kind==='reply'){setPreview(r.observation);setAiMessage(r.clarification_fa||'برداشت آماده بررسی شماست.');return}
      setProducts(r.products);setSearchDiagnostics([]);setRecommendations(r.recommendations);setSearched(true)
      setDiscoveryParent(!target&&r.products.length?state.id:null)
      const comparisonIDs=r.comparison_product_ids||[]
      setComparisonSuggestion(comparisonIDs.length===2?{products:comparisonIDs.map(id=>r.products.find(p=>p.product_id===id)!).filter(Boolean),constraints:r.proposed_constraints}:null)
      setAiMessage(r.clarification_fa||'این گزینه‌ها از داده موجود پیدا شدند؛ شواهد هر پیشنهاد را می‌توانید ببینید.')
      setProposal({constraints:r.proposed_constraints,missionId:target?.missionId||null,baseRevision:target?.baseRevision||null,summary:r.proposal_summary?.eligible_shops})
    }catch(e){if(aiEpoch.current===epoch){setAiPending(false);activeTurn.current=null;setTurn(null);setError(shortError(e));if(kind==='needs'){setDiscoveryParent(null);setComparisonSuggestion(null)}}}
  }
  async function openReply(offerId:string){
    if(!mission)return
    replyTrigger.current=document.activeElement as HTMLElement
    setError('');setBusy(true);await cancelAI(true)
    try{const f=await api.post<Followup>(`/api/missions/${mission.id}/followups`,{offer_id:offerId});setFollowup({...f,missionId:mission.id,baseRevision:mission.revision});setPreview(null);setReplyText('');setOutcome('unavailable');setQuote('');setClosureDate(localInput(new Date()).slice(0,10));setAiMessage('')}catch(e){setError(shortError(e))}finally{setBusy(false)}
  }
  async function manualPreview(){
    if(!followup)return
    await cancelAI(true)
    setError('');setBusy(true)
    try{const value=outcome==='price_change'?parseToman(quote):null;if(outcome==='price_change'&&value===null)throw new Error('قیمت تازه را وارد کنید.')
      const p=await api.post<Observation>(`/api/missions/${followup.missionId}/observations/preview`,{followup_id:followup.id,expected_revision:followup.baseRevision,kind:outcome,raw_text:replyText,price_toman:value,effective_visit_date:outcome==='closed'?closureDate:null});setPreview(p)
    }catch(e){setError(shortError(e))}finally{setBusy(false)}
  }
  async function confirmReply(){
    if(!followup||!preview)return
    setBusy(true);setError('')
    try{const r=await api.post<MissionResponse>(`/api/missions/${followup.missionId}/observations/${preview.id}/confirm`,{expected_revision:preview.base_revision});accept(r);setDelta(r.delta!);setPreview(null);setFollowup(null);setToast('گزارش ثبت شد؛ شرایط خرید شما حفظ شدند.');revealMission()}catch(e){setError(shortError(e));setPreview(null)}finally{setBusy(false)}
  }
  async function reset(){if(!mission)return;setError('');setBusy(true);await cancelAI(true);try{const r=await api.post<MissionResponse>(`/api/missions/${mission.id}/reset`,{expected_revision:mission.revision});accept(r);setDelta(null);setFollowup(null);setPreview(null);setToast('فقط گزارش‌های این شبیه‌سازی پاک شدند.')}catch(e){setError(shortError(e))}finally{setBusy(false)}}
  async function copy(text:string){try{await navigator.clipboard.writeText(text);setToast('متن کپی شد.')}catch{setToast('کپی خودکار ممکن نیست؛ متن نمایش‌داده‌شده را انتخاب و کپی کنید.')}}
  function openCompare(){try{setCompareConstraints(readDraft(draft));setShowCompare(true)}catch(e){setError(shortError(e))}}
  async function useSearchDiagnostic(d:SearchDiagnostic){setDiscoveryParent(null);setComparisonSuggestion(null);setDraft(draftOf(d.constraints));setBusy(true);setError('');await cancelAI(true);try{const r=await api.post<{products:Product[];diagnostics:SearchDiagnostic[]}>('/api/search',d.constraints);setDiscoveryParent(null);setComparisonSuggestion(null);setProducts(r.products);setSearchDiagnostics(r.diagnostics||[]);setRecommendations([]);setSearched(true);setToast('فقط شرایط جست‌وجو با انتخاب شما تغییر کرد؛ برنامه قبلی تغییر نکرد.')}catch(e){setError(shortError(e))}finally{setBusy(false)}}
  function locate(){if(!navigator.geolocation){setError('موقعیت‌یابی در دسترس نیست؛ مختصات یا محدوده جمهوری را انتخاب کنید.');return}navigator.geolocation.getCurrentPosition(p=>{interactionEpoch.current++;setDraft(d=>({...d,lat:String(p.coords.latitude),lon:String(p.coords.longitude),originLabel:'موقعیت دستگاه'}));setToast('موقعیت در فرم قرار گرفت؛ برای تغییر برنامه آن را اعمال کنید.')},()=>setError('دسترسی موقعیت در دسترس نیست؛ از محدوده جمهوری یا مختصات دستی استفاده کنید.'),{timeout:7000})}
  function toggleCompare(p:Product){setCompared(items=>items.some(x=>x.product_id===p.product_id)?items.filter(x=>x.product_id!==p.product_id):items.length<2?[...items,p]:[items[1],p])}
  const active=aiPending||!!(turn&&['running','advancing'].includes(turn.state))
  const transport=actions.filter(a=>a.destination_text!==null)
  const primary=plan?.primary
  const budgetHint=(()=>{try{return formatToman(parseToman(draft.budget))}catch{return ''}})()

  return <div className="app-shell">
    <header className="app-header"><a className="brand" href="/" aria-label="پلن بی، صفحه اصلی"><span className="brand-mark"><ShoppingBag size={24}/></span><span><b>پلن بی</b><small>همراه خرید حضوری</small></span></a><div className="header-location"><MapPin size={16}/>تهران</div><a className="header-source" href="https://torob.com/" target="_blank" rel="noopener noreferrer">با داده‌های ترب<ExternalLink size={13}/></a></header>
    <main>
      <div className="intro"><div><h1>خریدت را از همین‌جا شروع کن.</h1><p>از انتخاب کالا تا فروشنده جایگزین؛ شرایط تو در برنامه می‌ماند.</p></div><button className="button demo-button" onClick={()=>void loadDemo()} disabled={busy||!ready}><span className="demo-mini"><i/><i/></span><span>دیدن سناریوی نمونه<small>خرید آزمایشی، بدون تماس با فروشگاه</small></span><ArrowLeft size={18}/></button></div>
      {error&&<div className="notice error" role="alert"><span>{error}</span>{initFailed&&<button className="button soft-button" onClick={()=>{setError('');setInitKey(x=>x+1)}}>تلاش دوباره برای اتصال</button>}<button onClick={()=>setError('')} aria-label="بستن خطا"><X size={17}/></button></div>}
      {toast&&<div className="notice toast" role="status"><span><Check size={16}/>{toast}</span><button onClick={()=>setToast('')} aria-label="بستن پیام"><X size={15}/></button></div>}
      {!ready&&<div className="notice">{error?'داده هنوز آماده نیست؛ صفحه را تازه کنید.':'در حال آماده‌کردن داده‌ها…'}</div>}
      <div className="workspace">
        <section className="discovery" aria-label="انتخاب کالا">
          <div className="section-heading"><h2>دستیار خرید حضوری</h2><span className={`model-status ${modelAvailable?'online':''}`}><i/>{modelAvailable?'دستیار آماده':'جست‌وجو و برنامه‌ریزی فعال'}</span></div>
          <section className="assistant-box" aria-label="گفت‌وگوی خرید"><div className="assistant-title"><Sparkles size={18}/><b>چی لازم داری؟ با هم انتخابش کنیم.</b></div><p className="agent-intro">نیازت را بگو؛ گزینه‌های داده را بررسی می‌کنم و تصمیم نهایی با توست.</p><label className="sr-only" htmlFor="need">نیاز شما</label><textarea id="need" value={need} onChange={e=>setNeed(e.target.value)} placeholder="نیازت را توضیح بده؛ مثل گوشی برای کار روزمره تا چهل میلیون…" rows={2}/><div className="origin-control"><button className="button compact-button" onClick={()=>setLocationOpen(true)}><MapPin size={15}/>انتخاب محدوده</button><span className="origin-label">مبدأ جست‌وجو: {draft.originLabel||'نقطه انتخاب‌شده'}<small><bdi>{Number(draft.lat).toFixed(4)}, {Number(draft.lon).toFixed(4)}</bdi>{mission?' • تغییر فرم تا تأیید، برنامه را تغییر نمی‌دهد.':''}</small></span></div><div className="assistant-actions">{mission&&<label>موضوع درخواست<Select label="موضوع درخواست" value={aiScope} onChange={e=>setAiScope(e.target.value as 'discovery'|'mission')}><option value="discovery">پیدا کردن کالا</option><option value="mission">شرایط همین کالا</option></Select></label>}<button className="button soft-button" disabled={!ready||!modelAvailable||active||busy} onClick={()=>void startAI('needs')}><Sparkles size={15}/>کمک برای انتخاب</button></div>
            {!modelAvailable&&<p className="source-note">دستیار فعلاً آنلاین نیست؛ جست‌وجو و بازچینی دستی در دسترس‌اند.</p>}
            {active&&<div className="ai-progress" role="status"><LoaderCircle className="spin" size={17}/>{turn?.stage==='interpret'?'در حال فهم نیاز شما…':turn?.stage==='reply'?'در حال بررسی پاسخ…':'در حال بررسی شواهد کالاها…'}<button onClick={()=>void cancelAI()}>توقف بررسی</button></div>}
            {discoveryParent&&<p className="source-note discovery-context">ادامه گفت‌وگو درباره حداکثر شش گزینه اول همین پاسخ؛ اولی و دومی با ترتیب کارت‌ها مشخص‌اند.</p>}{userNeed&&<div className="user-turn"><small>درخواست شما</small><p>{userNeed}</p></div>}{!followup&&aiMessage&&<p className="ai-message" role="status">{aiMessage}</p>}
            {comparisonSuggestion&&comparisonSuggestion.products.length===2&&<div className="proposal comparison-suggestion"><b>مقایسه دو گزینه همین گفت‌وگو</b><p>جدول با شرایط نمایش‌داده‌شده باز می‌شود؛ فرم و برنامه خرید تغییر نمی‌کنند.</p><button className="button soft-button" onClick={()=>{setCompared(comparisonSuggestion.products);setCompareConstraints(comparisonSuggestion.constraints);setShowCompare(true)}}>مقایسه همین دو گزینه</button></div>}
            {proposal&&<div className="proposal"><b>پیشنهاد؛ هنوز اعمال نشده</b><span>بودجه: {proposal.constraints.max_price_toman?formatToman(proposal.constraints.max_price_toman)+' تومان':'بدون سقف'}</span><span>شعاع: {proposal.constraints.radius_km} کیلومتر</span><span>مراجعه: {faDate(proposal.constraints.visit_at)} {proposal.constraints.visit_at?localInput(proposal.constraints.visit_at).slice(11):'نامشخص'}</span><span>پرداخت: {proposal.constraints.payment_provider||'بدون شرط خاص'}</span>{proposal.summary!==undefined&&<span>گزینه‌های سازگار در این پیشنهاد: {new Intl.NumberFormat('fa-IR').format(proposal.summary)}</span>}<button className="button soft-button" onClick={()=>void applyProposal()} disabled={busy}>استفاده از پیشنهاد</button></div>}
          </section>
          <details className="manual-search"><summary><Search size={16}/>جست‌وجوی مستقیم و فیلترها</summary>
          <form className="search-form" onSubmit={e=>void manualSearch(e)}><fieldset disabled={busy}><label htmlFor="query">جست‌وجوی کالا</label><div className="search-row"><Search size={20}/><input id="query" value={draft.query} onChange={e=>updateDraft('query',e.target.value)} placeholder="مدل، برند یا نام کالا؛ مثلاً A07" autoComplete="off"/><button className="button primary-button" disabled={!ready||busy} type="submit">{busy?<LoaderCircle className="spin" size={18}/>:'جست‌وجو'}</button></div>
            <div className="filter-grid"><label>دسته‌بندی<Select label="دسته‌بندی" value={draft.category} onChange={e=>updateDraft('category',e.target.value)}><option value="">همه دسته‌ها</option><option>گوشی موبایل</option><option>لپ تاپ و نوت بوک</option></Select></label><label>بودجه به تومان<input value={draft.budget} onChange={e=>updateDraft('budget',e.target.value)} inputMode="numeric" placeholder="بدون سقف"/><small>{draft.budget?budgetHint+' تومان':'بدون محدودیت بودجه'}</small></label><label>شعاع، کیلومتر<input value={draft.radius} onChange={e=>updateDraft('radius',e.target.value)} inputMode="decimal"/></label><label>زمان مراجعه، تهران<input type="datetime-local" value={draft.visit} onChange={e=>updateDraft('visit',e.target.value)}/></label></div>
            <details className="location-settings"><summary><SlidersHorizontal size={15}/>محدوده و شرایط پرداخت</summary><div className="location-buttons"><button type="button" onClick={()=>{setDraft(d=>({...d,lat:String(DEMO.lat),lon:String(DEMO.lon),originLabel:DEMO.origin_label||''}));setToast('محدوده جمهوری در فرم انتخاب شد.')}}>محدوده جمهوری</button><button type="button" onClick={locate}><Navigation size={14}/>موقعیت من</button></div><div className="filter-grid compact-grid"><label>عرض جغرافیایی<input value={draft.lat} onChange={e=>updateDraft('lat',e.target.value)} inputMode="decimal" dir="ltr"/></label><label>طول جغرافیایی<input value={draft.lon} onChange={e=>updateDraft('lon',e.target.value)} inputMode="decimal" dir="ltr"/></label><label>شرط پرداخت<Select label="شرط پرداخت" value={draft.payment} onChange={e=>updateDraft('payment',e.target.value)}><option value="">بدون شرط خاص</option><option>ترب‌پی</option><option>اسنپ‌پی</option><option>دیجی پی</option><option>تارا</option></Select></label></div><label className="inline-check"><input type="checkbox" checked={draft.contactable} onChange={e=>updateDraft('contactable',e.target.checked)}/>فقط فروشگاه با وب‌سایت یا اینستاگرام ثبت‌شده</label><p className="source-note">مسیر تماس ثبت‌شده تضمین پاسخ‌گویی یا موجودی نیست؛ شماره‌های داده آزمایشی‌اند.</p><label className="inline-check"><input type="checkbox" checked={draft.open} onChange={e=>updateDraft('open',e.target.checked)}/>فقط سازگار با ساعت اعلام‌شده</label><p className="source-note">فاصله‌ها مستقیم‌اند. پذیرش اعلامی فروشگاه به معنی تأیید اعتبار شما نیست.</p></details>
            {mission&&<button type="button" className="button apply-conditions" disabled={busy||!!staleMissionId} onClick={()=>void applyConditions()}>اعمال شرایط روی همین برنامه</button>}
          </fieldset></form>
          </details>
          <div className="results-heading"><h2>{products.length?'کالاهای پیدا‌شده':'انتخاب از داده‌های موجود'}</h2>{compared.length>0&&<button className="button compact-button" onClick={openCompare} disabled={compared.length!==2}>مقایسه دو کالا ({new Intl.NumberFormat('fa-IR').format(compared.length)})</button>}</div>
          {products.length?<div className="product-grid">{products.map(p=><ProductCard key={p.product_id} product={p} busy={busy} recommendation={recommendations.find(r=>r.product_id===p.product_id)} compared={compared.some(x=>x.product_id===p.product_id)} onCompare={()=>toggleCompare(p)} onSelect={()=>void selectProduct(p)}/>)}</div>:<div className="empty-state"><ShoppingBag size={34}/><h3>{searched?'برای این جست‌وجو کالایی پیدا نشد.':'از یک نام یا نیاز شروع کن.'}</h3><p>{searched?'تطبیق دقیق عبارت با این دسته و بودجه نتیجه نداشت؛ این به معنی نبود کالا در بازار نیست.':'قیمت، مسیر و گزینه دوم بعد از انتخاب کالا کنار هم قرار می‌گیرند.'}</p><div className="search-diagnostics">{searchDiagnostics.map(d=><div key={d.kind}><p>{d.kind==='category'?'همین عبارت در دسته‌های دیگر نتیجه دارد.':`برای همین عبارت، قیمت ثبت‌شده از ${formatToman(d.minimum_toman)} تومان شروع می‌شود.`}</p><button className="button soft-button" disabled={busy} onClick={()=>void useSearchDiagnostic(d)}>{d.kind==='category'?'جست‌وجو در همه دسته‌ها':'جست‌وجو با این بودجه'}</button></div>)}</div><div className="examples">{['A07','Lenovo','گوشی 128'].map(q=><button key={q} onClick={()=>{updateDraft('query',q);editConditions();document.getElementById('query')?.focus()}}>{q}</button>)}</div></div>}
        </section>

        <aside id="mission" tabIndex={-1} className="mission-panel" aria-label="برنامه خرید">
          <div className="mission-heading"><span className="note-corner"/><h2>برنامه خریدت</h2><small>اول انتخاب، بعد استعلام، سپس مراجعه</small></div>
          {!mission||!product||!plan?<div className="mission-empty"><span className="paired-symbol"><i>۱</i><i>۲</i></span><h3>یک انتخاب، یک راه دوم</h3><p>کالا را انتخاب کن تا فروشنده اول، گزینه نزدیک جایگزین و اطلاعاتی که باید بررسی کنی اینجا بمانند.</p><div className="quiet-rule"/><p className="source-note">برنامه، تضمین موجودی یا رزرو کالا نیست.</p></div>:<>
            {mission.mode==='simulation'&&<div className="simulation-banner" data-testid="simulation-banner"><b>شبیه‌سازی روشن است</b><span>پاسخ‌ها آزمایشی‌اند؛ هیچ تماسی با فروشگاه گرفته نمی‌شود.</span><small>زمان مراجعه انتخاب‌شده: {faDate(mission.constraints.visit_at)}</small></div>}
            <div className="mission-product" data-testid="mission-product"><span>کالای انتخاب‌شده</span><h3>{product.title||'عنوان ثبت نشده'}</h3></div>
            <div className="locked-chips"><span>بودجه {mission.constraints.max_price_toman?formatToman(mission.constraints.max_price_toman):'بدون سقف'}</span><span>شعاع {new Intl.NumberFormat('fa-IR').format(mission.constraints.radius_km)} کیلومتر</span><span>مبدأ برنامه: {mission.constraints.origin_label||'نقطه انتخاب‌شده'}</span><span>{faDate(mission.constraints.visit_at)} {mission.constraints.visit_at?localInput(mission.constraints.visit_at).slice(11):''}</span>{mission.constraints.payment_provider&&<span>{mission.constraints.payment_provider}</span>}{mission.constraints.contactable_only&&<span>فقط مسیر تماس ثبت‌شده</span>}</div>
            {staleMissionId&&<div className="notice error" role="status"><p>برنامه در جای دیگری تغییر کرده؛ پیش از قبول پیشنهاد تازه، نسخه فعلی را بخوان.</p><button className="button soft-button" disabled={busy} onClick={()=>void refreshMission()}>تازه‌سازی برنامه</button></div>}
            {delta&&<div className="plan-delta" data-testid="plan-delta" role="status"><b>برنامه بازچینی شد</b><p>{delta.price_delta_toman!==null?(BigInt(delta.price_delta_toman)>0?`${formatToman(delta.price_delta_toman)} تومان بیشتر` :BigInt(delta.price_delta_toman)<0?`${formatToman(delta.price_delta_toman.slice(1))} تومان کمتر`:'قیمت گزینه اول تغییر نکرد'):'گزینه‌های سازگار دوباره بررسی شدند.'}</p><small>کالا، بودجه و شرایط مراجعه حفظ شدند.</small></div>}
            {primary?<><SellerCard option={primary} role="primary" disabled={busy} onFollowup={id=>void openReply(id)}/>{plan.fallback?<><div className="fallback-bridge"><span/><small>اگر گزینه اول نشد</small><span/></div><SellerCard option={plan.fallback} role="fallback" disabled={busy} onFollowup={id=>void openReply(id)}/></>:<div className="no-backup">گزینه دومِ نزدیک و سازگار ثبت نشده؛ پیش از مراجعه بیشتر بررسی کن.</div>}</>:<div className="no-match" role="status"><h3>با این شرایط، گزینه قابل برنامه‌ریزی نداریم.</h3><p>داده نامشخص یا پاسخ نگرفته را به‌جای گزینه معتبر معرفی نمی‌کنیم. شرایط را خودت تغییر بده یا دوباره استعلام کن.</p><div className="no-match-actions"><button className="button soft-button" onClick={editConditions}>ویرایش شرایط خرید</button><button className="button soft-button" onClick={()=>{const list=document.querySelector<HTMLDetailsElement>('.excluded-list');if(list){list.open=true;list.scrollIntoView({behavior:'smooth',block:'start'})}}}>بازبینی پاسخ‌های قبلی</button></div></div>}
            {!primary&&!!plan.relaxations?.length&&<section className="constraint-suggestions" aria-label="پیشنهاد تغییر یک شرط"><h3>با کمترین تغییرِ یک شرط</h3><p>کالا و همه شرط‌های دیگر حفظ می‌شوند؛ هنوز تغییر نکرده‌اند.</p>{plan.relaxations.map(s=><article key={s.field} data-testid="constraint-suggestion"><b>{s.field==='max_price_toman'?`بودجه را ${formatToman(s.delta)} تومان بیشتر کن`:`شعاع را به ${new Intl.NumberFormat('fa-IR').format(Number(s.value))} کیلومتر برسان`}</b><p>{s.field==='max_price_toman'?`بودجه جدید ${formatToman(String(s.value))} تومان؛ `:'فاصله مستقیم؛ '}{new Intl.NumberFormat('fa-IR').format(s.eligible_shops)} فروشگاه با شرایط دیگر سازگار می‌شود.</p><small>قیمت و ساعت تاریخی؛ موجودی همچنان نیازمند استعلام است.</small><button className="button soft-button" disabled={busy||!!staleMissionId} onClick={()=>void applyConditions(s.constraints,s.base_revision)}>قبول این تغییر</button></article>)}</section>}
            {plan.choices.length>1&&<div className="plan-choices"><b>انتخابت را عوض کن</b>{plan.choices.map(c=><button key={c.offer.offer_id} disabled={busy} onClick={async()=>{setError('');setBusy(true);await cancelAI(true);try{const r=await api.patch<MissionResponse>(`/api/missions/${mission.id}`,{expected_revision:mission.revision,selected_primary_shop_id:c.offer.shop_id});accept(r);setFollowup(null);setPreview(null)}catch(e){setError(shortError(e))}finally{setBusy(false)}}}>{c.tradeoffs.map(t=>(tradeoffLabels[t]||t)).join(' / ')}<small>{formatToman(c.offer.price_toman)} تومان</small></button>)}</div>}
            <div className="external-actions">{actions.filter(a=>a.destination_text===null).map(a=><a key={a.kind} className={a.kind==='torob_search'?'torob-link':''} href={a.url} target="_blank" rel="noopener noreferrer">{a.label}<ExternalLink size={14}/></a>)}{primary&&<button className="button transport-button" onClick={()=>setTransportOpen(v=>!v)}><Navigation size={16}/>رفتن به فروشگاه</button>}</div>
            {transportOpen&&primary&&<div className="transport-panel"><b>مقصد گزینه اول</b><p className="selectable">{transport[0]?.destination_text||primary.offer.address}</p><button onClick={()=>void copy(transport[0]?.destination_text||primary.offer.address)}><Copy size={14}/>کپی آدرس و مختصات</button><div className="transport-links">{transport.map(a=><a href={a.url} key={a.kind} target="_blank" rel="noopener noreferrer">{a.label}<ExternalLink size={13}/></a>)}</div><small>در بلد، اسنپ و تپسی آدرس را خودت وارد کن. رزرو سفر یا محاسبه کرایه انجام نمی‌شود.</small></div>}
            {plan.excluded.length>0&&<details className="excluded-list"><summary>چه چیزهایی نیازمند بررسی‌اند؟ ({new Intl.NumberFormat('fa-IR').format(plan.shortlist_coverage.excluded_offers)})</summary><ExcludedSellers options={plan.excluded} busy={busy} onFollowup={id=>void openReply(id)}/><p className="source-note">وضعیت نامشخص به معنی موجودی یا امکان خرید تأییدشده نیست.</p></details>}
            {history.length>0&&<details className="history"><summary>تغییرهای همین برنامه</summary>{history.map(h=><p key={h.after_revision}>گزارش {h.reason_codes.map(k=>outcomeLabels[k]||k).join('، ')}{h.price_delta_toman!==null?`؛ تغییر قیمت ${formatToman(h.price_delta_toman)} تومان`:''}</p>)}</details>}
            {mission.mode==='simulation'?<div className="simulation-controls"><button onClick={()=>void reset()} disabled={busy}><RefreshCcw size={14}/>بازنشانی شبیه‌سازی</button><button onClick={()=>void selectProduct(product,mission.constraints,'assisted')} disabled={busy}>شروع برنامه بدون شبیه‌سازی</button></div>:<button className="simulation-entry" onClick={()=>void selectProduct(product,mission.constraints,'simulation')} disabled={busy}>آزمایش این برنامه در شبیه‌سازی</button>}
          </>}
        </aside>
      </div>

      {followup&&mission&&<Dialog className="reply-panel" label="بررسی پاسخ فروشنده" initialFocus="textarea" returnFocus={replyTrigger.current} onClose={()=>{setFollowup(null);setPreview(null);void cancelAI(true)}}><div className="section-heading"><div><h2>یک پاسخ، یک تصمیم روشن‌تر</h2><p>{mission.mode==='simulation'?'این بخش شبیه‌سازی است؛ هیچ پیامی ارسال نشده.':'متن را خودت ارسال و پاسخ را وارد کن؛ این برنامه پیامی ارسال نمی‌کند.'}</p></div><button className="icon-button" aria-label="بستن بررسی پاسخ" onClick={()=>{setFollowup(null);setPreview(null);void cancelAI(true)}}><X/></button></div>
        {error&&<div className="notice error" role="alert">{error}</div>}
        {toast&&<div className="notice toast" role="status">{toast}</div>}
        {active&&<div className="ai-progress" role="status"><LoaderCircle className="spin" size={17}/>در حال بررسی پاسخ…<button onClick={()=>void cancelAI()}>توقف بررسی</button></div>}
        {aiMessage&&<p className="ai-message" role="status">{aiMessage}</p>}
        <div className="reply-grid"><div><h3>متن پیشنهادی استعلام</h3><p className="inquiry selectable">{followup.inquiry}</p><button className="button soft-button" onClick={()=>void copy(followup.inquiry)}><Copy size={15}/>کپی متن استعلام</button>{followup.contact_links.length?<div className="contact-links">{followup.contact_links.map(l=><a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer">{l.channel==='website'?'وب‌سایت ثبت‌شده':'اینستاگرام ثبت‌شده'}<ExternalLink size={13}/></a>)}</div>:<p className="source-note">مسیر تماس واقعی در این داده ثبت نشده؛ شماره آزمایشی نمایش داده نمی‌شود.</p>}</div>
          <div className="reply-inputs"><label>متن پاسخ فروشنده<textarea value={replyText} onChange={e=>{setReplyText(e.target.value);setPreview(null);void cancelAI(true)}} rows={3} placeholder="پاسخ را اینجا وارد کن؛ یا نتیجه بررسی را دستی انتخاب کن."/></label><button className="button soft-button" onClick={()=>void startAI('reply')} disabled={!modelAvailable||active||busy||!replyText.trim()}><Sparkles size={15}/>برداشت دستیار از پاسخ</button><div className="manual-observation"><label>نتیجه بررسی<Select label="نتیجه بررسی" value={outcome} onChange={e=>{setOutcome(e.target.value);setPreview(null)}}>{Object.entries(outcomeLabels).map(([key,label])=><option key={key} value={key} disabled={key==='payment_conflict'&&!mission.constraints.payment_provider}>{label}</option>)}</Select></label>{outcome==='price_change'&&<label>قیمت تازه به تومان<input value={quote} onChange={e=>{setQuote(e.target.value);setPreview(null)}} inputMode="numeric"/></label>}{outcome==='closed'&&<label>روز تعطیلی گزارش‌شده<input type="date" value={closureDate} onChange={e=>{setClosureDate(e.target.value);setPreview(null)}}/></label>}<button className="button primary-button" onClick={()=>void manualPreview()} disabled={busy}>پیش‌نمایش تغییر</button></div></div></div>
        {preview&&<div className="observation-preview" data-testid="observation-preview"><b>هنوز اعمال نشده؛ برداشت را بررسی کن</b><p>{outcomeLabels[preview.kind]}{preview.price_toman?` — ${formatToman(preview.price_toman)} تومان`:''}{preview.effective_visit_date?` — ${preview.effective_visit_date}`:''}</p><blockquote>{preview.raw_text||'نتیجه به‌صورت دستی انتخاب شده است.'}</blockquote><small>{preview.provenance==='simulation'?'منبع: شبیه‌سازی':'منبع: گزارش شما؛ تأیید مستقل فروشنده نیست'}</small><button className="button primary-button" onClick={()=>void confirmReply()} disabled={busy}>تأیید پاسخ و بازچینی<Check size={16}/></button></div>}
      </Dialog>}
    </main>
    {mission&&<button className="mission-jump button primary-button" onClick={revealMission}><ShoppingBag size={17}/>برنامه خریدم<ArrowLeft size={16}/></button>}
    <footer><span>پلن بی • نمونه چالش خرید حضوری ترب</span><p>قیمت و ساعت ثبت‌شده با موجودی و تأیید زنده متفاوت‌اند.</p></footer>
    {locationOpen&&<LocationChooser onClose={()=>setLocationOpen(false)} onSelect={p=>{interactionEpoch.current++;setDraft(d=>({...d,lat:String(p.lat),lon:String(p.lon),originLabel:p.label.slice(0,300)}));setLocationOpen(false);setToast('نقطه ثبت‌شده در فرم قرار گرفت؛ برای تغییر برنامه، شرایط را اعمال کن.')}}/>}
    {showCompare&&compareConstraints&&<ProductComparison products={compared} constraints={compareConstraints} onClose={()=>setShowCompare(false)} onSelect={p=>{setShowCompare(false);void selectProduct(p,compareConstraints)}}/>}
  </div>
}
