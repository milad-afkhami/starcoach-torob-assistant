import {useState} from 'react'
import {MapPin,Search,X} from 'lucide-react'
import {api} from './api'
import {Dialog} from './Dialog'
import type {LocationPoint} from './types'

export function LocationChooser({onSelect,onClose}:{onSelect:(p:LocationPoint)=>void;onClose:()=>void}){
 const [query,setQuery]=useState(''),[points,setPoints]=useState<LocationPoint[]>([]),[busy,setBusy]=useState(false),[searched,setSearched]=useState(false),[error,setError]=useState('')
 async function search(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');try{const r=await api.get<{locations:LocationPoint[]}>(`/api/locations?q=${encodeURIComponent(query.trim())}`);setPoints(r.locations);setSearched(true)}catch(e){setError(e instanceof Error?e.message:'نشانی پیدا نشد.')}finally{setBusy(false)}}
 return <Dialog label="انتخاب محدوده جست‌وجو" className="location-dialog" onClose={onClose} initialFocus="input"><div className="section-heading"><h2>از کجای تهران شروع می‌کنی؟</h2><button className="icon-button" aria-label="بستن انتخاب محدوده" onClick={onClose}><X/></button></div><p>نام خیابان یا بخشی از نشانی را بنویس و یک نقطه نزدیک را مبدأ محدوده قرار بده.</p><form onSubmit={e=>void search(e)}><label>نام خیابان یا نشانی<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="مثلاً جمهوری، تجریش یا صادقیه" maxLength={100}/></label><button className="button primary-button" disabled={busy||query.trim().length<2}><Search size={16}/>پیدا کردن نشانی</button></form>{error&&<p role="alert">{error}</p>}<div className="location-results">{points.map(p=><button key={p.shop_id} data-testid="location-result" onClick={()=>onSelect(p)}><MapPin size={17}/><span>{p.label}<small>نقطه ثبت‌شده در داده؛ مبدأ محدوده شما</small></span></button>)}</div>{searched&&!points.length&&<p role="status">نشانی مطابق این عبارت در داده نیست. نام خیابان را کوتاه‌تر کن، یا از موقعیت دستگاه و مختصات دستی استفاده کن.</p>}<p className="source-note">این جست‌وجو از نشانی و مختصات فروشگاه‌های دیتاست است؛ مرکز محله یا نشانی شما را حدس نمی‌زنیم. داده همه مناطق تهران را پوشش نمی‌دهد. انتخاب فقط در فرم قرار می‌گیرد؛ تغییر برنامه نیازمند تأیید شماست.</p></Dialog>
}
