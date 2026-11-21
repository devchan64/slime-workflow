import React from "react";
import MockProgress from "./MockProgress.jsx";

export default function AnimateMockPage() {
  return <main><h1>Animate-2 격리 모의 검증</h1>
    <p>실제 생성과 재개는 메모리 부족으로 보류 중입니다. 아래에서 입력 구성을 확인하고 모의 작업 상태를 조회할 수 있습니다.</p>
    <fieldset><legend>캐릭터 동작 전사 입력</legend>
      <label>캐릭터 참조 PNG · 832×480<input type="file" accept="image/png"/></label>
      <label>RGB 동작 MP4 · 16fps 샘플링<input type="file" accept="video/mp4"/></label>
      <label>캐릭터 외형·배경 설명<textarea maxLength={8000}/></label>
      <label>프레임<input type="number" min={5} max={81} step={4} defaultValue={21}/></label>
      <label>스텝<input type="number" min={2} max={50} defaultValue={40}/></label>
      <label>시드<input type="number" min={0} max={2147483647} defaultValue={0}/></label>
    </fieldset>
    <MockProgress scope="animate2"/>
  </main>;
}
