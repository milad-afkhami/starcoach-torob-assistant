import {Children,isValidElement,useEffect,useId,useRef,useState} from 'react'
import type {ChangeEvent,KeyboardEvent,ReactNode} from 'react'
import {Check,ChevronDown} from 'lucide-react'

type Option={value:string;label:string;disabled:boolean}
/** Select-only combobox. The button keeps focus; aria-activedescendant identifies the active option. */
export function Select({value,onChange,children,label,disabled=false}:{value:string;onChange:(event:ChangeEvent<HTMLSelectElement>)=>void;children:ReactNode;label:string;disabled?:boolean}){
 const id=useId(),root=useRef<HTMLSpanElement>(null),trigger=useRef<HTMLButtonElement>(null)
 const options:Option[]=Children.toArray(children).filter(isValidElement).map(child=>{const p=child.props as {value?:string;children:ReactNode;disabled?:boolean};return {value:String(p.value??p.children),label:String(p.children),disabled:!!p.disabled}})
 const selected=Math.max(0,options.findIndex(x=>x.value===value))
 const [open,setOpen]=useState(false),[active,setActive]=useState(selected)
 useEffect(()=>{if(!open)return;const close=(e:PointerEvent)=>{if(!root.current?.contains(e.target as Node))setOpen(false)};document.addEventListener('pointerdown',close);return()=>document.removeEventListener('pointerdown',close)},[open])
 useEffect(()=>{if(open)document.getElementById(`${id}-${active}`)?.scrollIntoView({block:'nearest'})},[active,open,id])
 function choose(i:number){const option=options[i];if(!option||option.disabled)return;onChange({target:{value:option.value}} as ChangeEvent<HTMLSelectElement>);setOpen(false);trigger.current?.focus()}
 function move(direction:number){let i=active;for(let n=0;n<options.length;n++){i=(i+direction+options.length)%options.length;if(!options[i].disabled){setActive(i);return}}}
 function key(event:KeyboardEvent<HTMLButtonElement>){
  if(['ArrowDown','ArrowUp','Home','End','Enter',' '].includes(event.key))event.preventDefault()
  if(event.key==='Escape'){event.preventDefault();event.stopPropagation();setOpen(false);return}
  if(event.key==='Tab'){setOpen(false);return}
  if(event.key==='ArrowDown'||event.key==='ArrowUp'){if(!open){setActive(selected);setOpen(true)}else move(event.key==='ArrowDown'?1:-1);return}
  if(event.key==='Home'||event.key==='End'){setOpen(true);const indices=options.map((_,i)=>i).filter(i=>!options[i].disabled);setActive(event.key==='Home'?indices[0]:indices.at(-1)!);return}
  if(event.key==='Enter'||event.key===' '){if(open)choose(active);else{setActive(selected);setOpen(true)};return}
  if(event.key.length===1){const i=options.findIndex(o=>!o.disabled&&o.label.startsWith(event.key));if(i>=0){setActive(i);setOpen(true)}}
 }
 return <span className="select-control" ref={root}>
  <button ref={trigger} type="button" className="select-trigger" role="combobox" aria-label={label} aria-expanded={open} aria-controls={`${id}-list`} aria-haspopup="listbox" aria-activedescendant={open?`${id}-${active}`:undefined} disabled={disabled} onKeyDown={key} onClick={()=>{setActive(selected);setOpen(v=>!v)}}><span>{options[selected]?.label}</span><ChevronDown size={16} aria-hidden="true"/></button>
  {open&&<span id={`${id}-list`} role="listbox" aria-label={label} className="select-options">{options.map((option,i)=><span id={`${id}-${i}`} key={option.value} role="option" aria-selected={option.value===value} aria-disabled={option.disabled} className={`select-option ${i===active?'active':''}`} onPointerMove={()=>{if(!option.disabled)setActive(i)}} onPointerDown={e=>e.preventDefault()} onClick={e=>{e.preventDefault();e.stopPropagation();choose(i)}}><span>{option.label}</span>{option.value===value&&<Check size={15} aria-hidden="true"/>}</span>)}</span>}
 </span>
}
