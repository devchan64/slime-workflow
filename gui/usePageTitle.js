import {useEffect} from "react";
export default function usePageTitle(title,embedded){
  useEffect(()=>{if(!embedded && title)document.title=title;},[embedded,title]);
}
