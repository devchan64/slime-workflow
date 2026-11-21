import React,{useId} from "react";

export default function ActionButton({children,reasons=[],disabled=false,type="button",onClick}) {
  const id=useId();
  const unmet=reasons.filter(Boolean);
  return <div className="action-button">
    {unmet.length>0 && <p id={id}>{unmet.join(" ")}</p>}
    <button type={type} disabled={disabled || unmet.length>0} aria-describedby={unmet.length ? id : undefined} onClick={onClick}>{children}</button>
  </div>;
}
