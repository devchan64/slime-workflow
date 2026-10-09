// Gradio는 일반 조작부를 담당하고 이 컴포넌트는 이미지 재생만 담당한다.
let currentFramePayload={}, currentFrameIndex=0, currentPlaybackTimer=null;
let currentRequestSequence=0, currentDirectionName='', currentPlaybackRate=8;
const stopFramePlayback=()=>{clearInterval(currentPlaybackTimer);currentPlaybackTimer=null;};
const showPlayerMessage=currentMessageText=>{element.querySelector('[data-player-status]').textContent=currentMessageText;return currentMessageText;};
const readSelectedFrames=()=>currentFramePayload.frames?.[currentDirectionName]||[];
const drawSelectedFrame=()=>{
 const currentFramePaths=readSelectedFrames();
 const currentImageContainer=element.querySelector('[data-player-images]');
 const currentGridColumns=Number.isInteger(currentFramePayload.columns)&&currentFramePayload.columns>0?currentFramePayload.columns:null;
 currentImageContainer.style.display=currentGridColumns?'grid':'flex';
 currentImageContainer.style.gridTemplateColumns=currentGridColumns?`repeat(${currentGridColumns},minmax(0,1fr))`:'';
 const currentRequestNumber=++currentRequestSequence;
 if(!currentFramePaths.length){currentImageContainer.replaceChildren();showPlayerMessage(currentFramePayload.message||'표시할 결과 프레임이 없습니다.');return;}
 const currentFrameNumber=currentFrameIndex;
 const currentSourceNumber=currentFramePayload.sourceFrames?.[currentDirectionName]?.[currentFrameNumber];
 const currentFrameLabel=(currentSourceNumber===undefined?'':`원본 ${currentSourceNumber} · `)+`${currentFrameNumber+1} / ${currentFramePaths.length} 프레임`;
 const currentPanelPaths=Array.isArray(currentFramePaths[currentFrameNumber])?currentFramePaths[currentFrameNumber]:[currentFramePaths[currentFrameNumber]];
 showPlayerMessage(currentFrameLabel+' · 불러오는 중');
 // 모든 패널의 같은 프레임이 준비된 뒤 한 번에 교체한다.
 Promise.all(currentPanelPaths.map(currentImagePath=>new Promise((resolveFrameImage,rejectFrameImage)=>{
  const currentPendingImage=new Image();
  currentPendingImage.onload=()=>resolveFrameImage(currentPendingImage);
  currentPendingImage.onerror=()=>rejectFrameImage(new Error('프레임 이미지 로딩 실패'));
  currentPendingImage.src=currentFramePayload.directUrls?currentImagePath:currentFramePayload.base+'/character-animation/files/'+currentFramePayload.id+'/'+currentImagePath;
 }))).then(currentPanelImages=>{
  if(currentRequestNumber!==currentRequestSequence||!element.isConnected)return;
  const currentPanelElements=currentPanelImages.map((currentPanelImage,currentPanelIndex)=>{
   const currentPanelFigure=document.createElement('figure');
   currentPanelFigure.style.flex='1';currentPanelFigure.style.minWidth='0';
   currentPanelImage.alt=currentFramePayload.panels?.[currentPanelIndex]||'생성 결과 프레임';
   currentPanelImage.style.maxWidth='100%';currentPanelImage.style.maxHeight='560px';currentPanelImage.style.objectFit='contain';
   currentPanelFigure.append(currentPanelImage);
   if(currentFramePayload.panels?.[currentPanelIndex]){
    const currentPanelCaption=document.createElement('figcaption');currentPanelCaption.textContent=currentFramePayload.panels[currentPanelIndex];currentPanelFigure.append(currentPanelCaption);
   }
   return currentPanelFigure;
  });
  currentImageContainer.replaceChildren(...currentPanelElements);showPlayerMessage(currentFrameLabel);
 }).catch(()=>{
  if(currentRequestNumber!==currentRequestSequence)return;
  stopFramePlayback();currentImageContainer.replaceChildren();showPlayerMessage('프레임 이미지를 불러오지 못했습니다. 결과를 다시 조회하세요.');
 });
};
const moveSelectedFrame=currentFrameDelta=>{
 const currentFrameCount=readSelectedFrames().length;
 if(currentFrameCount){currentFrameIndex=(currentFrameIndex+currentFrameDelta+currentFrameCount)%currentFrameCount;drawSelectedFrame();}
};
const loadPlayerPayload=()=>{
 stopFramePlayback();++currentRequestSequence;currentFrameIndex=0;
 try{currentFramePayload=props.value?JSON.parse(props.value):{};}
 catch(currentParseError){currentFramePayload={};showPlayerMessage('재생 결과 형식 오류');return;}
 currentDirectionName=Object.keys(currentFramePayload.frames||{})[0]||'';
 let currentDownloadContainer=element.querySelector('[data-player-downloads]');
 if(!currentDownloadContainer){currentDownloadContainer=document.createElement('div');currentDownloadContainer.dataset.playerDownloads='';element.querySelector('[data-player-status]').after(currentDownloadContainer);}
 currentDownloadContainer.replaceChildren();
 const currentDownloadTable=document.createElement('table');
 const currentTableCaption=document.createElement('caption');currentTableCaption.textContent='결과 다운로드';currentDownloadTable.append(currentTableCaption);
 const currentTableHeader=currentDownloadTable.createTHead().insertRow();
 for(const currentColumnLabel of ['파일명','다운로드']){
  const currentHeaderCell=document.createElement('th');currentHeaderCell.scope='col';currentHeaderCell.textContent=currentColumnLabel;currentTableHeader.append(currentHeaderCell);
 }
 const currentTableBody=currentDownloadTable.createTBody();
 for(const currentArtifactRecord of currentFramePayload.downloads||[]){
  const currentArtifactUrl=new URL(currentArtifactRecord.url,window.location.href);
  if(currentArtifactUrl.protocol!=='http:'||currentArtifactUrl.hostname!=='127.0.0.1')continue;
  const currentDownloadAnchor=document.createElement('a');currentDownloadAnchor.href=currentArtifactUrl.href;currentDownloadAnchor.setAttribute('download','');
  const currentDownloadIcon=document.createElement('span');currentDownloadIcon.textContent='⤓';currentDownloadIcon.setAttribute('aria-hidden','true');
  currentDownloadAnchor.append(currentDownloadIcon,document.createTextNode(' 다운로드'));
  currentDownloadAnchor.setAttribute('aria-label',currentArtifactRecord.label+' 다운로드');
  const currentDownloadRow=currentTableBody.insertRow();
  currentDownloadRow.insertCell().textContent=currentArtifactRecord.label;
  currentDownloadRow.insertCell().append(currentDownloadAnchor);
 }
 if(currentTableBody.rows.length)currentDownloadContainer.append(currentDownloadTable);
 if(currentFramePayload.deferLoading){element.querySelector('[data-player-images]').replaceChildren();showPlayerMessage('미리보기 불러오기를 눌러 선택한 프레임을 확인하세요.');}
 else drawSelectedFrame();
};
window.generationFramePlayerCommands??={};
window.generationFramePlayerCommands[currentPlayerIdentifier]=(currentActionName,selectedDirectionName,selectedPlaybackRate,selectedFrameNumber)=>{
 const wasFramePlaybackActive=currentPlaybackTimer!==null;
 stopFramePlayback();
 const nextDirectionName=selectedDirectionName==='first'?Object.keys(currentFramePayload.frames||{})[0]:selectedDirectionName;
 if(!currentFramePayload.frames?.[nextDirectionName]?.length){return showPlayerMessage('선택한 방향에 결과가 없습니다. 등록 첫 방향을 선택하거나 다른 결과를 조회하세요.');}
 if(currentDirectionName!==nextDirectionName){currentDirectionName=nextDirectionName;currentFrameIndex=0;drawSelectedFrame();}
 currentPlaybackRate=Number(selectedPlaybackRate);
 if(![4,8,12,16].includes(currentPlaybackRate)){return showPlayerMessage('지원하지 않는 재생 FPS입니다.');}
 if(currentActionName==='configure'){drawSelectedFrame();if(wasFramePlaybackActive)currentPlaybackTimer=setInterval(()=>{if(!element.isConnected){stopFramePlayback();return;}moveSelectedFrame(1);},1000/currentPlaybackRate);}
 else if(currentActionName==='load')drawSelectedFrame();
 else if(currentActionName==='previous')moveSelectedFrame(-1);
 else if(currentActionName==='next')moveSelectedFrame(1);
 else if(currentActionName==='seek'){
  if(!Number.isInteger(selectedFrameNumber)||selectedFrameNumber<1||selectedFrameNumber>readSelectedFrames().length){return showPlayerMessage(`1–${readSelectedFrames().length} 사이의 프레임 번호를 입력하세요.`);}
  currentFrameIndex=selectedFrameNumber-1;drawSelectedFrame();
 }else if(currentActionName==='play')currentPlaybackTimer=setInterval(()=>{if(!element.isConnected){stopFramePlayback();return;}moveSelectedFrame(1);},1000/currentPlaybackRate);
 return currentActionName==='play'?'재생 중입니다. 재생 중지로 멈출 수 있습니다.':currentActionName==='stop'?'재생을 중지했습니다.':'프레임 이동을 요청했습니다. 위 이미지의 프레임 번호를 확인하세요.';
};
watch('value',loadPlayerPayload);
loadPlayerPayload();
