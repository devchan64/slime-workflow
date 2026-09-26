// 페이지는 이동 대상만 선언하고 공통 탐색·도움말 표현은 여기서 관리한다.
(() => {
 const sectionTargetElements=[...document.querySelectorAll('[data-workflow-label]')];
 if(!sectionTargetElements.length)return;
 const navigationContainer=document.createElement('nav');navigationContainer.className='workflow-navigation';navigationContainer.setAttribute('aria-label','작업 영역 바로가기');
 sectionTargetElements.forEach((sectionTargetElement,sectionTargetIndex)=>{
  if(!sectionTargetElement.id)sectionTargetElement.id='workflow-section-'+sectionTargetIndex;
  const navigationActionButton=document.createElement('button');navigationActionButton.type='button';navigationActionButton.textContent=`${sectionTargetIndex+1}. ${sectionTargetElement.dataset.workflowLabel}`;
  navigationActionButton.onclick=()=>{sectionTargetElement.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});sectionTargetElement.setAttribute('tabindex','-1');sectionTargetElement.focus({preventScroll:true});};
  navigationContainer.append(navigationActionButton);
 });
 const pageHeaderElement=document.querySelector('header');
 if(pageHeaderElement)pageHeaderElement.after(navigationContainer);else document.querySelector('main').before(navigationContainer);
 document.querySelectorAll('[data-help-title]').forEach(helpContentElement=>{
  const helpDetailsElement=document.createElement('details'),helpSummaryElement=document.createElement('summary');
  helpDetailsElement.className='workflow-help';helpSummaryElement.textContent=helpContentElement.dataset.helpTitle;
  helpContentElement.before(helpDetailsElement);helpDetailsElement.append(helpSummaryElement,helpContentElement);
 });
})();

if(window.top===window&&!document.querySelector('script[src="/management/gpu-status.js"]')){const gpuStatusScript=document.createElement('script');gpuStatusScript.src='/management/gpu-status.js';document.head.append(gpuStatusScript);}
