import { MapPin, MessageSquareText, ExternalLink, Clock3 } from 'lucide-react'
import { faDate, formatToman } from './format'
import type { Option } from './types'

export const reasonLabels: Record<string,string> = {
  over_budget: 'بالاتر از بودجه', outside_radius: 'بیرون محدوده', closed_at_visit: 'خارج از ساعت اعلام‌شده',
  hours_unknown: 'ساعت نامشخص', price_missing: 'قیمت نامشخص', price_flagged: 'قیمت نیازمند بررسی',
  location_unknown: 'موقعیت نامشخص', payment_unknown: 'شرایط پرداخت نامشخص', payment_conflict: 'ناسازگار با شرط پرداخت',
  reported_unavailable: 'ناموجود گزارش شده', no_response: 'بی‌پاسخ؛ نیازمند بررسی', variant_mismatch: 'مدل یا مشخصات متفاوت',
  reported_payment_conflict: 'پرداخت ناسازگار گزارش شده', reported_closed: 'تعطیلی گزارش شده', quote_required: 'نیازمند استعلام جداگانه',
}
export const outcomeLabels: Record<string,string> = {
  unavailable: 'ناموجود', available: 'موجود اعلام شده', no_response: 'پاسخی نگرفتم',
  price_change: 'قیمت تغییر کرده', variant_mismatch: 'مدل یا مشخصات متفاوت است', payment_conflict: 'شرط پرداخت پذیرفته نشد', closed: 'فروشگاه تعطیل است',
}

export function SellerCard({option,role,onFollowup,compact=false,disabled=false}:{option:Option;role:'primary'|'fallback'|'excluded';onFollowup?:(id:string)=>void;compact?:boolean;disabled?:boolean}) {
  const o=option.offer
  return <article className={`seller-card ${role} ${compact?'compact':''}`} data-testid={`${role}-card`}>
    <div className="seller-top"><span className="seller-role">{role==='primary'?'گزینه اول':role==='fallback'?'گزینه دوم، نزدیک شما':'نیازمند توجه'}</span>
      <span className="distance"><MapPin size={13}/>{o.straight_line_km===null?'فاصله نامشخص':`${new Intl.NumberFormat('fa-IR',{maximumFractionDigits:2}).format(o.straight_line_km)} کیلومتر`}</span></div>
    <h3>{o.shop_name || 'فروشگاه بدون نام'}</h3>
    {o.identity_anonymized && <span className="source-note">نام ناشناس‌شده در داده آزمایشی</span>}
    <div className="seller-price"><bdi>{formatToman(o.price_toman)}</bdi>{o.price_toman!==null&&<small>تومان</small>}</div>
    <p className="price-caption">{o.observation_provenance?'قیمت/وضعیت با گزارش نشست':'قیمت ثبت‌شده'}{o.observation_provenance==='simulation'?' • شبیه‌سازی':''} • {faDate(o.price_changed_at)}</p>
    <div className="facts-line"><span className="stock-unknown">موجودی نامشخص</span><span><Clock3 size={13}/>{o.hours_state==='open'?'سازگار با ساعت اعلام‌شده':o.hours_state==='closed'?'خارج از ساعت اعلام‌شده':'ساعت نامشخص'}</span></div>
    <p className="address"><MapPin size={15}/><span>{o.address||'آدرس ثبت نشده'}</span></p>
    {option.reason_codes.length>0&&<div className="reason-list">{option.reason_codes.map(r=><span key={r}>{reasonLabels[r]||'نیازمند بررسی'}</span>)}</div>}
    {o.observations.map(x=><p className="observation-note" key={x.id}>{outcomeLabels[x.kind]||x.kind} — {x.provenance==='simulation'?'شبیه‌سازی':'گزارش شما'}</p>)}
    {!compact&&<>
      <details className="source-details"><summary>اطلاعات ثبت‌شده و محدودیت‌ها</summary><p>ساعت‌ها اعلامی و قیمت‌ها تاریخی‌اند؛ قبل از مراجعه، قیمت، موجودی و ساعت را بررسی کنید.</p>
        <p>عنوان فروشنده: {o.seller_title||'نامشخص'}</p><p>گارانتی: {o.warranty||'ثبت نشده'}</p>
        <p>قیمت اصلی داده: <bdi>{formatToman(o.recorded_price_toman)}</bdi></p>
        {o.contact_links.map(l=><a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer">{l.channel==='website'?'وب‌سایت ارائه‌شده':'اینستاگرام ارائه‌شده'} <ExternalLink size={13}/></a>)}
        {!o.contact_links.length&&<p>مسیر تماس واقعی برای این فروشگاه در داده ثبت نشده است. شماره‌های داده آزمایشی قابل استفاده نیستند.</p>}
      </details>
    </>}
      {onFollowup&&!o.contact_links.length&&<p className="source-note contact-gap">مسیر تماس واقعی در داده نیست؛ فقط متن استعلام و گزارش شما بررسی می‌شود.</p>}
      {onFollowup&&<button className={`button ${role==='primary'?'primary-button':'soft-button'}`} disabled={disabled} onClick={()=>onFollowup(o.offer_id)}><MessageSquareText size={17}/>بررسی پاسخ فروشنده</button>}
  </article>
}
