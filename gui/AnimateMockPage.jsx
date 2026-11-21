import AnimateInputs from "./AnimateInputs.jsx";
import React from "react";
import MockProgress from "./MockProgress.jsx";

export default function AnimateMockPage() {
  return <main><h1>Animate-2 격리 모의 검증</h1>
    <p>실제 생성과 재개는 메모리 부족으로 보류 중입니다. 아래에서 입력 구성을 확인하고 모의 작업 상태를 조회할 수 있습니다.</p>
    <AnimateInputs/>
    <MockProgress scope="animate2"/>
  </main>;
}
