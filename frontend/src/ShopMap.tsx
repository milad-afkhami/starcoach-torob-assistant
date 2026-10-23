import {useEffect,useRef,useState} from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type {Plan} from './types'
import {formatToman} from './format'

/** Closed source-backed map: no geocoding, inferred positions, routes or model markup. */
export function ShopMap({plan}:{plan:Plan}){
 const host=useRef<HTMLDivElement>(null),map=useRef<L.Map|null>(null),markers=useRef(new Map<string,L.Marker>())
 const [selected,setSelected]=useState<string|null>(plan.primary?.offer.shop_id||null),[failed,setFailed]=useState(false),[loading,setLoading]=useState(true)
 const shops=[{option:plan.primary,label:'گزینه اول',role:'primary'},{option:plan.fallback,label:'گزینه دوم',role:'fallback'}].flatMap(x=>x.option?[{...x,offer:x.option.offer}]:[])
 const points=shops.filter(s=>s.offer.lat!==null&&s.offer.lon!==null&&Number.isFinite(s.offer.lat)&&Number.isFinite(s.offer.lon)&&Math.abs(s.offer.lat)<=90&&Math.abs(s.offer.lon)<=180)
 useEffect(()=>{
  if(!host.current||!points.length)return
  const m=L.map(host.current,{scrollWheelZoom:false}).setView([points[0].offer.lat!,points[0].offer.lon!],16);map.current=m;setFailed(false);setLoading(true)
  let loaded=false;const timeout=setTimeout(()=>{if(!loaded){setLoading(false);setFailed(true)}},6000)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,referrerPolicy:'strict-origin-when-cross-origin',attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).on('tileload',()=>{loaded=true;clearTimeout(timeout);setLoading(false)}).on('tileerror',()=>{setLoading(false);setFailed(true)}).addTo(m)
  for(const s of points){
   const label=`${s.label}: ${s.offer.shop_name||'فروشگاه بدون نام'}`
   const marker=L.marker([s.offer.lat!,s.offer.lon!],{keyboard:true,title:label,alt:label,icon:L.divIcon({className:`shop-marker ${s.role}`,html:s.role==='primary'?'۱':'۲',iconSize:[36,42],iconAnchor:[18,42]})}).addTo(m)
   marker.on('click',()=>setSelected(s.offer.shop_id));marker.on('keydown',(event:L.LeafletKeyboardEvent)=>{if(['Enter',' '].includes(event.originalEvent.key)){L.DomEvent.stop(event.originalEvent);setSelected(s.offer.shop_id)}});markers.current.set(s.offer.shop_id,marker)
  }
  m.fitBounds(L.latLngBounds(points.map(s=>[s.offer.lat!,s.offer.lon!])),{padding:[45,45],maxZoom:17})
  const observer=new ResizeObserver(()=>m.invalidateSize());observer.observe(host.current)
  return()=>{clearTimeout(timeout);observer.disconnect();markers.current.clear();m.remove();map.current=null}
 },[plan])
 useEffect(()=>{for(const [id,marker] of markers.current){const element=marker.getElement();element?.classList.toggle('selected',id===selected);element?.setAttribute('aria-pressed',String(id===selected))}},[selected,plan])
 function select(id:string){setSelected(id);const marker=markers.current.get(id);if(marker)map.current?.panTo(marker.getLatLng(),{animate:false})}
 const current=shops.find(s=>s.offer.shop_id===selected)
 return <section className="shop-map" aria-label="نقشه فروشگاه‌های همین کالا"><h3>فروشگاه‌ها روی نقشه</h3><p className="source-note">نقاط ثبت‌شده در داده؛ قرمز گزینه اول، آبی گزینه دوم. مسیر و موجودی زنده بررسی نشده‌اند.</p>
  {points.length?<div className="map-canvas" ref={host} aria-label="نقشه تعاملی؛ با کلیدهای جهت جابه‌جا شوید"/>:<p>مختصات معتبری برای این گزینه‌ها ثبت نشده؛ نشانی‌ها را بررسی کن.</p>}
  {!!points.length&&loading&&!failed&&<p className="map-loading" role="status">در حال بارگذاری خیابان‌های نقشه… نشانگرها از مختصات ثبت‌شده‌اند.</p>}
  {failed&&<p className="map-failure" role="status">نقشه زمینه بارگذاری نشد. نشانگرها از مختصات داده‌اند؛ نشانی و انتخاب فروشگاه در فهرست زیر در دسترس است.</p>}
  <div className="map-shop-list">{shops.map(s=><button key={s.offer.shop_id} className={s.role} aria-pressed={selected===s.offer.shop_id} onClick={()=>select(s.offer.shop_id)}><b>{s.label}: {s.offer.shop_name||'نام ثبت نشده'}</b><small>{formatToman(s.offer.price_toman)} تومان · {s.offer.lat===null||s.offer.lon===null?'مختصات نامشخص':`${s.offer.lat.toFixed(5)}, ${s.offer.lon.toFixed(5)}`}</small></button>)}</div>
  {current&&<p className="map-selection" role="status">در حال مشاهده {current.label}: {current.offer.shop_name}. {current.offer.address||'نشانی ثبت نشده'}. انتخاب روی نقشه، ترتیب برنامه خرید را تغییر نمی‌دهد.</p>}
 </section>
}
