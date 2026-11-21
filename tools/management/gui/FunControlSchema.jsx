import React, {createContext, useContext} from "react";
import {JSONUIProvider, Renderer, defineRegistry} from "@json-render/react";
import {defineCatalog} from "@json-render/core";
import {schema} from "@json-render/react/schema";
import {z} from "zod";
import MediaJobResult from "./MediaJobResult.jsx";

const Context=createContext(null);
const catalog=defineCatalog(schema,{components:{
  Group:{props:z.object({}),slots:["default"]},
  Attachment:{props:z.object({field:z.string(),label:z.string(),accept:z.string()})},
  Prompt:{props:z.object({field:z.string(),label:z.string()})},
  Model:{props:z.object({})},
  Frames:{props:z.object({})},
  NumberField:{props:z.object({field:z.string(),label:z.string(),min:z.number(),step:z.union([z.number(),z.string()])})},
  Duration:{props:z.object({})},
  Result:{props:z.object({})}
}});
const {registry}=defineRegistry(catalog,{components:{
  Group:({children})=><>{children}</>,
  Attachment:({props})=>{const c=useContext(Context),{field,label,accept}=props;return <><label>{label}<input type="file" accept={accept} onChange={e=>c.attach(e.target.files[0],field)}/></label>
    {field==="images" && c.request.images[0] && <img alt="외형 참조 이미지" style={{maxWidth:"100%"}} src={"data:image/png;base64,"+c.request.images[0]}/>}
    {field==="pose_video" && c.request.pose_video && <video controls loop playsInline preload="metadata" aria-label="입력 포즈 영상" src={"data:video/mp4;base64,"+c.request.pose_video}/>}
    {field==="pose_video" && c.videoInfo && <div><p>{c.videoInfo.summary}</p><button type="button" onClick={()=>c.setRequest({...c.request,frames:c.frameLimit})}>입력 영상의 최대 프레임 적용</button></div>}</>},
  Prompt:({props})=>{const c=useContext(Context);return <label>{props.label}<textarea maxLength={8000} value={c.request[props.field]} onChange={e=>c.setRequest({...c.request,[props.field]:e.target.value})}/></label>},
  Model:()=>{const c=useContext(Context);return <label>모델<select value={c.request.model_profile || "wan22-14b"} onChange={e=>c.setRequest({...c.request,model_profile:e.target.value})}>{c.template.models?.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}</select></label>},
  Frames:()=>{const c=useContext(Context);return <fieldset><legend>출력 프레임 빠른 선택</legend>{[21,41,81,129].filter(n=>n<=c.frameLimit).map(n=><button key={n} type="button" aria-pressed={Number(c.request.frames)===n} onClick={()=>c.setRequest({...c.request,frames:n})}>{n}프레임</button>)}</fieldset>},
  NumberField:({props})=>{const c=useContext(Context);let max=props.field==="frames"?c.frameLimit:props.field==="seed"?c.template.maximum_seed:({steps:100,flow_shift:20,guidance_scale:10,switch_ratio:0.9})[props.field];return <label>{props.label}<input required type="number" min={props.min} max={max} step={props.step} value={c.request[props.field]} onChange={e=>c.setRequest({...c.request,[props.field]:e.target.value})}/></label>},
  Duration:()=>{const c=useContext(Context),n=Number(c.request.frames);return n>=5 && n<=c.template.maximum_frames && n%4===1 ? <p>출력 길이 {(n/16).toFixed(2)}초 · 16fps</p>:null},
  Result:()=>{const c=useContext(Context);return <MediaJobResult service="wan22-fun-control" id={c.job} folderLink={c.folderLink}>{c.children}</MediaJobResult>}
}});
const fields=[
  ["Attachment",{field:"images",label:"외형 참조 이미지",accept:"image/*"}],
  ["Attachment",{field:"pose_video",label:"처리된 포즈 MP4 · 832×480 · 16fps",accept:"video/mp4"}],
  ["Prompt",{field:"prompt",label:"동작 프롬프트"}],["Prompt",{field:"negative_prompt",label:"부정 프롬프트"}],
  ["Model",{}],["Frames",{}],
  ...[["frames","프레임 수",5,4],["steps","스텝",2,1],["seed","시드",0,1],["flow_shift","Flow shift",0.1,"any"],["guidance_scale","Guidance scale",1,"any"],["switch_ratio","모델 전환 비율",0.1,"any"]].map(([field,label,min,step])=>["NumberField",{field,label,min,step}]),["Duration",{}]
];
const inputSpec={root:"root",elements:{root:{type:"Group",props:{},children:fields.map((_,i)=>"f"+i)},...Object.fromEntries(fields.map(([type,props],i)=>["f"+i,{type,props}]))}};
const resultSpec={root:"result",elements:{result:{type:"Result",props:{}}}};
export function FunControlFields(props){return <Context.Provider value={props}><JSONUIProvider registry={registry}><Renderer spec={inputSpec} registry={registry}/></JSONUIProvider></Context.Provider>}
export function FunControlResult(props){return <Context.Provider value={props}><JSONUIProvider registry={registry}><Renderer spec={resultSpec} registry={registry}/></JSONUIProvider></Context.Provider>}
