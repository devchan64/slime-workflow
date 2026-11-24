import React from "react";
import PromptWordCount from "./PromptWordCount.jsx";

/** 검토 시점의 원문과 그 원문을 기준으로 센 단어 수를 함께 표시한다. */
export default function ReviewPrompt({label,text}) {
  const value=typeof text==="string" ? text : "";
  return <div className="review-prompt"><h3>{label}</h3><p className="fun-review-prompt">{value.trim() ? value : "없음"}</p><p><PromptWordCount text={value} label={label}/></p></div>;
}
