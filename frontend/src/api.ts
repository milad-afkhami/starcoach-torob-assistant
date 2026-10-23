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
async function request<T>(path: string, method: string, body?: unknown): Promise<T> {
  let response: Response
  try { response = await fetch(path, {method, credentials: 'same-origin', headers: body === undefined ? undefined : {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)}) }
  catch { throw new Error('ارتباط برقرار نشد؛ دوباره تلاش کنید.') }
  const value = await response.json().catch(()=>({}))
  if (!response.ok) throw new ApiError(typeof value.detail === 'string' ? value.detail : null,response.status)
  return value as T
}
export const api = {
  get: <T,>(path: string)=>request<T>(path,'GET'),
  post: <T,>(path: string,body: unknown = {})=>request<T>(path,'POST',body),
  patch: <T,>(path: string,body: unknown)=>request<T>(path,'PATCH',body),
}
