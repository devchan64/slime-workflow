import React from "react";

/** 편집 상태를 유지하면서 현재 대화를 별도 탭에서 연다. */
export default function ConversationLink(){
  const session=new URLSearchParams(typeof location === "undefined" ? "" : location.search).get("session");
  const href="/management/frame/hermes-agent/"+(session ? "?"+new URLSearchParams({session}) : "");
  return <a className="conversation-return-link" href={href} target="_blank" rel="noopener noreferrer">헤르메스 대화 새 탭에서 열기</a>;
}
