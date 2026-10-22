import { useLayoutEffect, useRef, type ReactNode } from 'react'

/** Native modality makes background controls inert and contains keyboard focus. */
export function Dialog({children,label,onClose,className,initialFocus,returnFocus}:{children:ReactNode;label:string;onClose:()=>void;className:string;initialFocus?:string;returnFocus?:HTMLElement|null}){
  const ref=useRef<HTMLDialogElement>(null)
  const close=useRef(onClose);close.current=onClose
  useLayoutEffect(()=>{
    const dialog=ref.current!
    const previous=returnFocus||document.activeElement as HTMLElement|null
    dialog.showModal()
    if(initialFocus)dialog.querySelector<HTMLElement>(initialFocus)?.focus()
    const cancel=(e:Event)=>{e.preventDefault();close.current()}
    dialog.addEventListener('cancel',cancel)
    return()=>{dialog.removeEventListener('cancel',cancel);dialog.close();if(previous?.isConnected)previous.focus({preventScroll:true})}
  },[])
  return <dialog ref={ref} className={className} aria-label={label}>{children}</dialog>
}
