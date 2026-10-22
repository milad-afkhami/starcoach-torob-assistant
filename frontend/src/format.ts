export function normalizeDigits(value: string): string {
  return value.replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 1776))
    .replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 1632)).replaceAll('٫', '.')
}

export function parseToman(value: string): string | null {
  const raw = normalizeDigits(value).replace(/[,٬\s]/g, '')
  if (!raw) return null
  if (!/^\d{1,19}$/.test(raw)) throw new Error('بودجه را به تومان و بدون اعشار بنویسید.')
  return BigInt(raw).toString()
}

export function formatToman(value: string | null | undefined): string {
  if (value == null || !/^-?\d+$/.test(value)) return 'قیمت نامشخص'
  return new Intl.NumberFormat('fa-IR').format(BigInt(value))
}

export function localInput(value: Date | string): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tehran', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23', calendar: 'gregory',
  }).formatToParts(new Date(value))
  const p = Object.fromEntries(parts.map(x => [x.type, x.value]))
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`
}

export function visitIso(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error('زمان مراجعه را کامل انتخاب کنید.')
  const iso = `${value}:00+03:30`
  if (!Number.isFinite(Date.parse(iso)) || localInput(iso) !== value) throw new Error('زمان مراجعه معتبر نیست.')
  return iso
}

export function faDate(value: string | null | undefined): string {
  if (!value || !Number.isFinite(Date.parse(value))) return 'تاریخ نامشخص'
  return new Intl.DateTimeFormat('fa-IR', { timeZone: 'Asia/Tehran', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(value))
}
