import KimodoPromptExamples from "./KimodoPromptExamples.jsx";
import GeneratorHistory from "./GeneratorHistory.jsx";
import GeneratorChangelog from "./GeneratorChangelog.jsx";
import TranslationEvidence from "./TranslationEvidence.jsx";
import React, {useEffect, useRef, useState} from "react";

function readSteps(definition) {
  if (!definition.trim()) return [];
  const parsed = JSON.parse(definition);
  if (!Array.isArray(parsed?.steps) || Object.keys(parsed).length !== 1 ||
      parsed.steps.some(step => !step || typeof step.id !== "string" || typeof step.generator !== "string"))
    throw new Error("현재 정의의 steps 목록을 확인하세요.");
  return parsed.steps;
}

export default function StepBuilder({call, definition, onChange, proposalStep}) {
  const [catalog, setCatalog] = useState({});
  const [generator, setGenerator] = useState("");
  const [name, setName] = useState("");
  const [inputs, setInputs] = useState({});
  const [links, setLinks] = useState({});
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    call("workflow-catalog").then(result => {if (active) setCatalog(result.generators);})
      .catch(error => {if (active) setNotice(error.message);});
    return () => { active = false; };
  }, [call]);
  const editor=useRef(null);
  useEffect(()=>{
    if(!proposalStep)return;
    setGenerator("kimodo");
    setInputs(proposalStep.inputs);
    setLinks({});
    setName("");
    setNotice("제안을 불러왔습니다. 단계 이름을 입력하고 워크플로우에 추가하세요.");
    editor.current.open=true;
    editor.current.scrollIntoView({block:"nearest"});
  },[proposalStep]);
  const template = catalog[generator];
  let steps = [], invalid = "";
  try { steps = readSteps(definition); } catch (error) { invalid = error.message; }
  function choose(key) {
    setGenerator(key);
    setInputs({});
    setLinks({});
    setNotice("");
  }
  function append() {
    try {
      const id = name.trim();
      if (!id || steps.some(step => step.id === id)) throw new Error("고유한 단계 이름을 입력하세요.");
      const values = {}, bindings = {};
      for (const [field,spec] of Object.entries(template.inputs)) {
        if (links[field]) {
          const [from_step, output, selection] = JSON.parse(links[field]);
          const source = steps.find(step => step.id === from_step);
          if (catalog[source?.generator]?.outputs[output]?.type !== spec.type) throw new Error("선행 단계 연결을 다시 선택하세요.");
          bindings[field] = selection ? {from_step, output, selection} : {from_step, output};
          continue;
        }
        const raw = inputs[field];
        if (raw === undefined || raw === "") {
          if (spec.required && spec.default === undefined) throw new Error((spec.label || field) + " 값을 입력하세요.");
          if (spec.default !== undefined) values[field] = spec.default;
        } else if (spec.type === "integer") {
          const number = Number(raw);
          if (!Number.isSafeInteger(number)) throw new Error(field + "에 정수를 입력하세요.");
          values[field] = number;
        } else if (spec.type === "glossary") {
          values[field] = raw.split(/\r?\n/).filter(line => line.trim()).map(line => {
            const terms = line.split("=>").map(term => term.trim());
            if (terms.length !== 2 || terms.some(term => !term)) throw new Error("용어마다 원문 => 번역어 한 쌍을 입력하세요.");
            return {source:terms[0], target:terms[1]};
          });
        } else if (spec.type === "png_list") values[field] = JSON.parse(raw);
        else values[field] = raw;
      }
      const step = {id, generator, generator_version:template.version, template_version:template.template_version, inputs:values, bindings};
      onChange(JSON.stringify({steps:[...steps,step]},null,2));
      setName(""); choose("");
    } catch (error) { setNotice(error.message); }
  }
  function editTextInput(index,field,value) {
    const next = steps.map((step,i)=>i===index ? {...step,inputs:{...step.inputs,[field]:value}} : step);
    onChange(JSON.stringify({steps:next},null,2));
  }
  return <>{steps.map((step,index)=>{
    const fields=Object.entries(step.inputs || {}).filter(([field,value])=>{
      const spec=catalog[step.generator]?.inputs?.[field];
      return spec && typeof value==="string" && !spec.choices && !step.bindings?.[field];
    });
    return fields.length>0 && <fieldset key={step.id}><legend>{step.id} · 입력 수정</legend>
      {fields.map(([field,value])=><label key={field}>{catalog[step.generator].inputs[field].label || field}
        <textarea value={value} maxLength={catalog[step.generator].inputs[field].max_length}
          onChange={event=>editTextInput(index,field,event.target.value)}/></label>)}
    </fieldset>;
  })}<details ref={editor}><summary>생성기 단계 추가</summary>
    <label>생성기 <select value={generator} onChange={event => choose(event.target.value)}>
      <option value="">생성기 선택</option>
      {Object.entries(catalog).map(([key,spec]) => <option key={key} value={key}>{spec.label}</option>)}
    </select></label>
    {generator && !template && Object.keys(catalog).length>0 && <p role="alert">현재 관리 서버의 생성기 목록에서 {generator} 템플릿을 찾을 수 없습니다.</p>}
    {template && <><label>단계 이름 <input value={name} onChange={event => setName(event.target.value)}/></label>
      {Object.entries(template.inputs).map(([field,spec]) => {
        if (spec.choices?.length===1 && spec.choices[0]===spec.default) return null;
        const sources = steps.flatMap(step => Object.entries(catalog[step?.generator]?.outputs || {})
          .filter(([,output]) => output.type === spec.type)
          .map(([key,output]) => ({value:JSON.stringify([step.id,key]),label:step.id+" · "+output.label})));
        const sourceLink = links[field] ? JSON.parse(links[field]) : [];
        const fallback = spec.default ?? "";
        const value = inputs[field] ?? (Array.isArray(fallback) ? JSON.stringify(fallback) : fallback);
        const props = {value, onChange:event => setInputs({...inputs,[field]:event.target.value})};
        return <div key={field}><label>{spec.label || field} {links[field] ? null : spec.choices ?
          <select {...props}>{spec.choices.map(choice => <option key={choice}>{choice}</option>)}</select> :
          spec.type==="glossary" ? <textarea {...props} placeholder="한 줄에 하나씩 원문 => 번역어"/> :
          <input {...props} type={spec.type==="integer"?"number":"text"} title={spec.help}
            min={spec.min} max={spec.max} step={spec.step} maxLength={spec.max_length}/>}</label>
          {field==="seed" && !links[field] && <button onClick={()=>setInputs({...inputs,seed:String(crypto.getRandomValues(new Uint32Array(1))[0] % (spec.max + 1))})}>랜덤 시드</button>}
          {sources.length>0 && <select aria-label={(spec.label || field)+" 입력 출처"} value={sourceLink.length ? JSON.stringify(sourceLink.slice(0,2)) : ""}
            onChange={event => setLinks({...links,[field]:event.target.value})}><option value="">직접 입력</option>
            {sources.map(source => <option key={source.value} value={source.value}>{source.label}</option>)}</select>}
          {sourceLink.length>0 && <label><input type="checkbox" checked={sourceLink[2]==="user_choice"}
            onChange={event=>setLinks({...links,[field]:JSON.stringify(event.target.checked?
              [...sourceLink.slice(0,2),"user_choice"]:sourceLink.slice(0,2))})}/>
            {spec.label || field}에 전달하기 전 결과 확인</label>}
        </div>;
      })}
      {generator==="kimodo" && !links.prompt && <KimodoPromptExamples apply={prompt=>setInputs({...inputs,prompt})}/>}
      {generator==="prompt-translation" && <GeneratorHistory service={generator} statusCommand="translation-status" restore={request=>{
        setInputs({text:request.text,target_language:request.target_language,
          glossary:(request.glossary || []).map(term=>term.source+" => "+term.target).join("\n")});
        setLinks({});
        setNotice("번역 작업의 입력을 불러왔습니다.");
      }}/>}
      <GeneratorChangelog key={generator} generator={generator==="flux-image" ? "flux-image-generator" : generator}/>
      {generator==="prompt-translation" && !links.text &&
        <TranslationEvidence key={inputs.text || ""} source={inputs.text || ""} call={call}/>}
      <button disabled={Boolean(invalid)} onClick={append}>편집 중인 정의에 단계 추가</button>
    </>}
    {(notice || invalid) && <p role="status">{notice || invalid}</p>}
  </details></>;
}
