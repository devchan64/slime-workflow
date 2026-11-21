import React from "react";
import {countPromptWords} from "./promptWords.mjs";
export default function PromptWordCount({text,label="원문",final=false}) {
  const words=countPromptWords(text);
  return <span className="prompt-word-count">{label} {words}단어{final && <> · 최종 {words}단어</>}</span>;
}
