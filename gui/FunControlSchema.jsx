import ReferenceImageInput from "./ReferenceImageInput.jsx";
import PromptWordCount from "./PromptWordCount.jsx";
import SeedInput from "./SeedInput.jsx";
import React, {createContext, useContext, useRef} from "react";
import {JSONUIProvider, Renderer, defineRegistry} from "@json-render/react";
import {defineCatalog} from "@json-render/core";
import {schema} from "@json-render/react/schema";
import {z} from "zod";
import MediaJobResult from "./MediaJobResult.jsx";

const Context=createContext(null);
export function FunModelDescription({profile}){
  return <small>{profile==="wan21-1.3b" ? "단일 모델로 모든 단계를 실행하며 모델 전환 비율을 적용하지 않습니다." : "고노이즈·저노이즈 모델을 전환 비율에 따라 사용합니다."}</small>;
}
const catalog=defineCatalog(schema,{components:{
  Group:{props:z.object({}),slots:["default"]},
  Section:{props:z.object({label:z.string()}),slots:["default"]},
  Advanced:{props:z.object({}),slots:["default"]},
  Attachment:{props:z.object({field:z.string(),label:z.string(),accept:z.string()})},
  Prompt:{props:z.object({field:z.string(),label:z.string()})},
  Model:{props:z.object({})},
  Frames:{props:z.object({})},
  SeedComparison:{props:z.object({})},
  NumberField:{props:z.object({field:z.string(),label:z.string(),min:z.number(),step:z.union([z.number(),z.string()])})},
  Duration:{props:z.object({})},
  Result:{props:z.object({})}
}});
const {registry}=defineRegistry(catalog,{components:{
  Group:({children})=><>{children}</>,
  Section:({props,children})=><fieldset className="fun-field-group"><legend>{props.label}</legend>{props.label==="첨부"?<div className="fun-attachments">{children}</div>:children}</fieldset>,
  Advanced:({children})=><details className="fun-advanced"><summary>고급 설정</summary>{children}</details>,
  Attachment:({props})=>{const c=useContext(Context),fileInput=useRef(null),{field,label,accept}=props;return <div className={"fun-attachment"+(field==="pose_video" ? " fun-attachment-pose" : "")}>{field==="images" ? <ReferenceImageInput disabled={c.busy} label={label} source={c.request.images[0] ? "data:image/png;base64,"+c.request.images[0] : ""} onSelectionStart={c.onImageSelectionStart} onChange={file=>file ? c.attach(file,field) : c.setRequest({...c.request,images:[]})}/> : <><span>{label}</span><label className="reference-image-file fun-pose-file">영상 파일 선택<input ref={fileInput} type="file" aria-label={label} accept={accept} disabled={c.busy} onChange={async e=>{const input=e.currentTarget;if(!await c.attach(input.files[0],field))input.value="";}}/></label></>}
    {field==="pose_video" && c.request.pose_video && <><p role="status">포즈 영상이 적용되어 있습니다. 파일을 선택하면 교체됩니다.</p><video className="fun-attachment-preview" controls loop playsInline preload="metadata" aria-label="입력 포즈 영상" src={"data:video/mp4;base64,"+c.request.pose_video}/><button type="button" disabled={c.busy} onClick={()=>{if(fileInput.current)fileInput.current.value="";c.removePose();requestAnimationFrame(()=>fileInput.current?.focus());}}>포즈 영상 제거</button></>}
    {field==="pose_video" && c.videoInfo && <div><p>{c.videoInfo.summary}</p><button type="button" onClick={()=>c.setRequest({...c.request,frames:c.frameLimit})}>입력 영상의 최대 프레임 적용</button></div>}</div>},
  Prompt:({props})=>{const c=useContext(Context);return <label>{props.label}<textarea maxLength={8000} value={c.request[props.field]} onChange={e=>c.setRequest({...c.request,[props.field]:e.target.value})}/><PromptWordCount text={c.request[props.field]} final/></label>},
  Model:()=>{const c=useContext(Context);return <label>모델<select value={c.request.model_profile || "wan22-14b"} onChange={e=>c.setRequest({...c.request,model_profile:e.target.value})}>{c.template.models?.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}</select><FunModelDescription profile={c.request.model_profile}/></label>},
  Frames:()=>{const c=useContext(Context);return <fieldset><legend>출력 프레임 빠른 선택</legend><div className="choice-buttons">{[21,41,81,129].filter(n=>n<=c.frameLimit).map(n=><button key={n} type="button" aria-pressed={Number(c.request.frames)===n} onClick={()=>c.setRequest({...c.request,frames:n})}>{n}프레임 · {(n/16).toFixed(2)}초</button>)}</div></fieldset>},
  SeedComparison:()=>{const c=useContext(Context);if(c.sourceSeed===null)return null;return <section className="seed-comparison" aria-label="시드 비교"><div><span>원본 시드</span><strong>{c.sourceSeed}</strong></div><div><span>현재 시드</span><strong>{c.request.seed}</strong></div><button type="button" disabled={c.busy} onClick={()=>{let next=crypto.getRandomValues(new Uint32Array(1))[0] & 0x7fffffff;if(next===c.sourceSeed || next===Number(c.request.seed))next=(next+1)%2147483648;if(next===c.sourceSeed)next=(next+1)%2147483648;c.setRequest({...c.request,seed:next});}}>다른 시드 선택</button>{Number(c.request.seed)===c.sourceSeed && <p role="status">원본과 같은 시드입니다.</p>}</section>},
  NumberField:({props})=>{const c=useContext(Context);if(props.field==="seed")return <SeedInput value={c.request.seed} max={c.template.maximum_seed} onChange={value=>c.setRequest({...c.request,seed:value})}/>;let max=props.field==="frames"?c.frameLimit:props.field==="seed"?c.template.maximum_seed:({steps:100,flow_shift:20,guidance_scale:10,switch_ratio:0.9})[props.field];return <label>{props.label}<input required type="number" min={props.min} max={max} step={props.step} value={c.request[props.field]} onChange={e=>c.setRequest({...c.request,[props.field]:e.target.value})}/></label>},
  Duration:()=>{const c=useContext(Context),n=Number(c.request.frames);return n>=5 && n<=c.template.maximum_frames && n%4===1 ? <p>출력 길이 {(n/16).toFixed(2)}초 · 16fps</p>:null},
  Result:()=>{const c=useContext(Context);return <MediaJobResult service="wan22-fun-control" id={c.job} folderLink={c.folderLink} onReuse={c.onReuse}>{c.children}</MediaJobResult>}
}});
const inputSpec={root:"root",elements:{
  root:{type:"Group",props:{},children:["attachments","prompts","settings"]},
  attachments:{type:"Section",props:{label:"첨부"},children:["image","pose"]},
  image:{type:"Attachment",props:{field:"images",label:"외형 참조 이미지",accept:"image/*"}},
  pose:{type:"Attachment",props:{field:"pose_video",label:"처리된 포즈 MP4 · 832×480 · 16fps",accept:"video/mp4"}},
  prompts:{type:"Section",props:{label:"프롬프트"},children:["prompt","negative"]},
  prompt:{type:"Prompt",props:{field:"prompt",label:"동작 프롬프트"}},
  negative:{type:"Prompt",props:{field:"negative_prompt",label:"부정 프롬프트"}},
  settings:{type:"Section",props:{label:"생성 설정"},children:["model","comparison","frames","frameCount","duration","seed","advanced"]},
  model:{type:"Model",props:{}},comparison:{type:"SeedComparison",props:{}},frames:{type:"Frames",props:{}},
  frameCount:{type:"NumberField",props:{field:"frames",label:"프레임 수",min:5,step:4}},duration:{type:"Duration",props:{}},
  seed:{type:"NumberField",props:{field:"seed",label:"시드",min:0,step:1}},
  advanced:{type:"Advanced",props:{},children:["steps","flow","guidance","ratio"]},
  steps:{type:"NumberField",props:{field:"steps",label:"스텝",min:2,step:1}},
  flow:{type:"NumberField",props:{field:"flow_shift",label:"Flow shift",min:0.1,step:"any"}},
  guidance:{type:"NumberField",props:{field:"guidance_scale",label:"Guidance scale",min:1,step:"any"}},
  ratio:{type:"NumberField",props:{field:"switch_ratio",label:"모델 전환 비율",min:0.1,step:"any"}}
}};
const resultSpec={root:"result",elements:{result:{type:"Result",props:{}}}};
export function FunControlFields(props){return <Context.Provider value={props}><JSONUIProvider registry={registry}><Renderer spec={inputSpec} registry={registry}/></JSONUIProvider></Context.Provider>}
export function FunControlResult(props){return <Context.Provider value={props}><JSONUIProvider registry={registry}><Renderer spec={resultSpec} registry={registry}/></JSONUIProvider></Context.Provider>}
