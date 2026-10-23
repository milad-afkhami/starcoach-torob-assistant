import type {Product} from './types'

export interface ComparisonRow {id:string;label:string;values:(string|null)[];sourceLabels:string[][]}
const keyOf=(value:string)=>value.toLowerCase().replace(/ي/g,'ی').replace(/ك/g,'ک').replace(/[\s\u200c\u200d_:\-]/g,'')
const aliases:Record<string,{id:string;label:string;quantity:boolean}>={}
for(const key of ['حافظه RAM','ظرفیت رم','حافظه رم','ظرفیت حافظه رم','مقدار رم'])aliases[keyOf(key)]={id:'ram-capacity',label:'حافظه رم',quantity:true}
for(const key of ['حافظه داخلی','ظرفیت حافظه داخلی','ظرفیت حافظه‌داخلی','ظرفیت ذخیره سازی داخلی'])aliases[keyOf(key)]={id:'internal-storage',label:'حافظه داخلی',quantity:true}
for(const key of ['سیستم عامل','سیستم‌عامل'])aliases[keyOf(key)]={id:'operating-system',label:'سیستم عامل',quantity:false}
function unitOf(value:string):string|null{
 if(/گیگابایت/.test(value)||/(?:^|[\s\d۰-۹٠-٩])GB\b/.test(value))return 'GB'
 if(/مگابایت/.test(value)||/(?:^|[\s\d۰-۹٠-٩])MB\b/.test(value))return 'MB'
 if(/ترابایت/.test(value)||/(?:^|[\s\d۰-۹٠-٩])TB\b/.test(value))return 'TB'
 return null
}
/** A small exact alias dictionary, not inferred product specs or unit conversion.
 * Keep unsupported/missing units separate; show original labels and values intact.
 */
export function comparisonRows(products:Product[]):ComparisonRow[]{
 const rows=new Map<string,ComparisonRow>()
 products.forEach((product,column)=>product.specs.forEach(spec=>{
  const key=(spec.key||spec.section||'مشخصه').trim(),section=(spec.section||'').trim(),value=spec.value?.trim()||null
  const alias=aliases[keyOf(key)],unit=alias?.quantity&&value?unitOf(value):null
  const useAlias=alias&&(!alias.quantity||unit!==null)
  const id=useAlias?`${alias.id}:${unit||'text'}`:`${keyOf(section)}:${keyOf(key)}`
  const row=rows.get(id)||{id,label:useAlias?alias.label:key,values:products.map(()=>null),sourceLabels:products.map(()=>[])}
  if(value){row.values[column]=row.values[column]?`${row.values[column]}، ${value}`:value;row.sourceLabels[column].push(key)}
  rows.set(id,row)
 }))
 const priorities=['حافظهداخلی','ظرفیتحافظه','حافظهرم','ظرفیترم','ظرفیتباتری','دوربیناصلی','ابعادنمایشگر','سیستمعامل','پردازنده','وزن','رنگ']
 const priority=(label:string)=>{const i=priorities.findIndex(key=>keyOf(label).includes(key));return i<0?100:i}
 return [...rows.values()].sort((a,b)=>priority(a.label)-priority(b.label))
}
