import React, {forwardRef} from "react";

// 복사 대상의 이름과 실제 복사 동작은 호출자가 제공한다.
const ClipboardCopyButton = forwardRef(function ClipboardCopyButton({label, title=label, ...buttonProps}, buttonRef) {
  return <button {...buttonProps} ref={buttonRef} type="button" className={["clipboard-copy-button", buttonProps.className].filter(Boolean).join(" ")} aria-label={label} title={title}><svg aria-hidden="true" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 4.5H6.75A1.75 1.75 0 0 0 5 6.25v13A1.75 1.75 0 0 0 6.75 21h10.5A1.75 1.75 0 0 0 19 19.25v-13a1.75 1.75 0 0 0-1.75-1.75H15"/><rect x="9" y="3" width="6" height="3" rx="1.25"/><path d="M9 11h6M9 15h6"/></svg></button>;
});

export default ClipboardCopyButton;
