const errors: Record<string,string> = {
  discovery_context_expired:'گفت‌وگوی قبلی قدیمی شده؛ نام کالا یا نیازت را دوباره بنویس.',
  invalid_discovery_context:'گزینه‌های این گفت‌وگو قابل ارجاع نیستند؛ یک جست‌وجوی تازه انجام بده.',
  unavailable: 'دستیار فعلاً در دسترس نیست؛ جست‌وجو و برنامه‌ریزی همچنان کار می‌کنند.',
  expired: 'زمان بررسی تمام شد. دوباره تلاش کنید یا از جست‌وجوی مستقیم استفاده کنید.',
  stale_revision: 'برنامه تغییر کرده است؛ پاسخ را برای نسخه تازه دوباره بررسی کنید.',
  stale_observation: 'این پیش‌نمایش قدیمی است؛ دوباره پاسخ را بررسی کنید.',
  turn_in_progress: 'یک بررسی در جریان است؛ ابتدا آن را تمام یا متوقف کنید.',
  rate_limited: 'درخواست‌های زیادی ثبت شده؛ کمی بعد دوباره تلاش کنید.',
  queue_full: 'دستیار مشغول است؛ جست‌وجوی مستقیم در دسترس است.',
  busy: 'دستیار مشغول است؛ کمی بعد دوباره تلاش کنید.',
  budget_exhausted: 'ظرفیت دستیار برای این بازه تمام شده؛ جست‌وجو و بازچینی فعال‌اند.',
  not_found: 'این برنامه در این نشست در دسترس نیست.',
  unauthenticated: 'نشست در دسترس نیست؛ صفحه را تازه کنید.',
  session_expired: 'نشست تمام شده؛ صفحه را تازه کنید.',
  invalid_quote: 'قیمت تازه را به تومان و بدون اعشار وارد کنید.',
  payment_requirement_missing: 'ابتدا شرط پرداخت موردنظر را در برنامه انتخاب کنید.',
  closure_date_required: 'روز تعطیلی گزارش‌شده را مشخص کنید.',
  invalid_output: 'پاسخ دستیار قابل تأیید نبود. اطلاعات ثبت‌شده و کنترل‌های دستی در دسترس‌اند.',
  provider_failed: 'بررسی دستیار انجام نشد؛ دوباره تلاش کنید یا دستی ادامه دهید.',
  catalogue_unavailable: 'داده‌های کالا در دسترس نیست؛ کمی بعد دوباره تلاش کنید.',
}
export function errorText(code: string | null | undefined): string {
  return errors[code || ''] || 'درخواست انجام نشد. اطلاعات را بررسی کنید و دوباره تلاش کنید.'
}
export class ApiError extends Error {
  readonly code:string|null; readonly status:number
  constructor(code:string|null,status:number){super(errorText(code));this.name='ApiError';this.code=code;this.status=status}
}
export class TransportError extends Error {
  constructor(){super('ارتباط برقرار نشد؛ دوباره تلاش کنید.');this.name='TransportError'}
}
async function request<T>(path: string, method: string, body?: unknown,signal?:AbortSignal): Promise<T> {
  let response: Response
  try { response = await fetch(path, {method, signal, credentials: 'same-origin', headers: body === undefined ? undefined : {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)}) }
  catch { throw new TransportError() }
  let value:Record<string,unknown>
  try{value=await response.json()}
  catch(error){
    if(!response.ok)throw new ApiError(null,response.status)
    if(error instanceof TypeError)throw new TransportError()
    throw new Error('پاسخ سرویس قابل خواندن نبود؛ دوباره تلاش کنید.')
  }
  if (!response.ok) throw new ApiError(typeof value.detail === 'string' ? value.detail : null,response.status)
  return value as T
}
export const api = {
  get: <T,>(path: string,signal?:AbortSignal)=>request<T>(path,'GET',undefined,signal),
  post: <T,>(path: string,body: unknown = {})=>request<T>(path,'POST',body),
  patch: <T,>(path: string,body: unknown)=>request<T>(path,'PATCH',body),
}


/** Three READ retries shared across this exact owned turn, within its original deadline.
 * POST creation/confirmation and non-transient HTTP failures are never replayed here.
 */
export function createTurnReader(id:string,deadline:number,isCurrent:()=>boolean,options?:{now:()=>number;wait:(ms:number)=>Promise<void>}){
  const now=options?.now||(()=>performance.now()),wait=options?.wait||((ms:number)=>new Promise<void>(resolve=>setTimeout(resolve,ms)))
  let retries=0,deadlineAbort=false
  function remaining(){const left=deadline-now();if(deadlineAbort||left<=0)throw new ApiError('expired',408);return left}
  return async function read<T>():Promise<T|null>{
    while(isCurrent()){
      const controller=new AbortController(),timer=setTimeout(()=>{deadlineAbort=true;controller.abort()},remaining())
      try{
        const value=await api.get<T>(`/api/turns/${encodeURIComponent(id)}`,controller.signal)
        if(!isCurrent())return null
        if(deadlineAbort)throw new ApiError('expired',408)
        remaining()
        return value
      }catch(error){
        if(!isCurrent())return null
        if(deadlineAbort)throw new ApiError('expired',408)
        remaining()
        const transient=error instanceof TransportError||(error instanceof ApiError&&[502,503,504].includes(error.status))
        if(!transient||retries>=3)throw error
        retries++
        await wait(Math.min(500*retries,remaining()))
      }finally{clearTimeout(timer)}
    }
    return null
  }
}
