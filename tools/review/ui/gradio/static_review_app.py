"""정적 검수 스냅샷을 Gradio 작업 영역의 사용자 정의 구성 요소로 제공한다."""
import argparse
import json
import os
import threading
import time
from pathlib import Path

import gradio as gr


STATIC_REVIEW_FRAME_HEIGHT=1000


def load_static_review_paths(source_file_path):
    source_record_values=json.loads(Path(source_file_path).read_text())
    static_review_paths={}
    for current_page_record in source_record_values.get('pages',[]):
        if current_page_record.get('uiMode')!='gradio-static':continue
        current_identifier_value=current_page_record.get('id')
        current_path_value=current_page_record.get('path')
        if not isinstance(current_identifier_value,str) or not current_identifier_value or not isinstance(current_path_value,str) or not current_path_value:
            raise ValueError('정적 검수 페이지 항목 형식 오류')
        static_review_paths[current_identifier_value]=current_path_value
    return static_review_paths


def create_static_review_loader(review_server_port, static_review_paths):
    serialized_paths=json.dumps(static_review_paths,ensure_ascii=False).replace('<','\\u003c')
    review_server_base=json.dumps(f'http://127.0.0.1:{review_server_port}')
    return f"""async()=>{{
const staticReviewRoot=document.querySelector('#static-review-root');
if(!staticReviewRoot||staticReviewRoot.dataset.staticReviewLoaded)return;
staticReviewRoot.dataset.staticReviewLoaded='true';
const staticReviewPaths={serialized_paths};
const reviewServerBase={review_server_base};
const reviewIdentifier=new URLSearchParams(window.location.search).get('review');
const selectedReviewPath=staticReviewPaths[reviewIdentifier];
if(!selectedReviewPath){{staticReviewRoot.innerHTML='<p class="static-review-error" role="alert">표시할 정적 검수 페이지를 찾을 수 없습니다.</p>';return;}}
const staticReviewPageLocation=new URL(selectedReviewPath,reviewServerBase);
staticReviewPageLocation.searchParams.set('embedded','gradio-static');
const staticReviewPageUrl=staticReviewPageLocation.href;
// 게임 디자인 검수의 스타일·모듈·상대 경로를 원래 문서 안에 격리한다.
if(selectedReviewPath.startsWith('ui-')&&!selectedReviewPath.split('?')[0].endsWith('-manager.html')){{
  const currentReviewFrame=document.createElement('iframe');
  currentReviewFrame.title='게임 디자인 검수';
  currentReviewFrame.width='100%';currentReviewFrame.height='{STATIC_REVIEW_FRAME_HEIGHT}';currentReviewFrame.setAttribute('frameborder','0');
  currentReviewFrame.src=staticReviewPageUrl;
  currentReviewFrame.addEventListener('load',()=>staticReviewRoot.setAttribute('aria-busy','false'));
  staticReviewRoot.replaceChildren(currentReviewFrame);
  return;
}}
const staticReviewAssetUrl=new URL('.',staticReviewPageUrl).href;
window.resolveStaticReviewAssetUrl=assetPathValue=>typeof assetPathValue==='string'&&!/^(?:[a-z]+:|[/])/i.test(assetPathValue)?new URL(assetPathValue,staticReviewAssetUrl).href:assetPathValue;
const originalFetchRequest=window.fetch.bind(window);
window.fetch=(requestValue,...requestOptionValues)=>{{
  if(typeof requestValue==='string'&&!/^(?:[a-z]+:|[/])/i.test(requestValue))return originalFetchRequest(new URL(requestValue,staticReviewAssetUrl),...requestOptionValues);
  return originalFetchRequest(requestValue,...requestOptionValues);
}};
try{{
  const staticReviewResponse=await originalFetchRequest(staticReviewPageUrl,{{cache:'no-store'}});
  if(!staticReviewResponse.ok)throw new Error('정적 검수 화면을 불러오지 못했습니다.');
  const staticReviewDocument=new DOMParser().parseFromString(await staticReviewResponse.text(),'text/html');
  for(const sourceStyleElement of staticReviewDocument.querySelectorAll('style')){{
    const nextStyleElement=document.createElement('style');nextStyleElement.dataset.staticReviewComponent='true';nextStyleElement.textContent=sourceStyleElement.textContent;document.head.append(nextStyleElement);
  }}
  for(const sourceLinkElement of staticReviewDocument.querySelectorAll('link[rel="stylesheet"]')){{
    const nextLinkElement=document.createElement('link');nextLinkElement.rel='stylesheet';nextLinkElement.href=new URL(sourceLinkElement.getAttribute('href'),staticReviewPageUrl).href;nextLinkElement.dataset.staticReviewComponent='true';document.head.append(nextLinkElement);
  }}
  for(const sourcePreloadElement of staticReviewDocument.querySelectorAll('link[rel="modulepreload"]')){{
    const nextPreloadElement=document.createElement('link');nextPreloadElement.rel='modulepreload';nextPreloadElement.href=new URL(sourcePreloadElement.getAttribute('href'),staticReviewPageUrl).href;nextPreloadElement.crossOrigin='anonymous';nextPreloadElement.dataset.staticReviewComponent='true';document.head.append(nextPreloadElement);
  }}
  const staticReviewMarkup=[...staticReviewDocument.body.children].filter(currentElementValue=>currentElementValue.tagName!=='SCRIPT').map(currentElementValue=>currentElementValue.outerHTML).join('');
  staticReviewRoot.innerHTML=staticReviewMarkup;
  for(const sourceScriptElement of staticReviewDocument.querySelectorAll('script')){{
    if(sourceScriptElement.type==='module'&&sourceScriptElement.src){{await import(new URL(sourceScriptElement.getAttribute('src'),staticReviewPageUrl).href);continue;}}
    const nextScriptElement=document.createElement('script');nextScriptElement.dataset.staticReviewComponent='true';
    if(sourceScriptElement.type)nextScriptElement.type=sourceScriptElement.type;
    if(sourceScriptElement.src){{nextScriptElement.src=new URL(sourceScriptElement.getAttribute('src'),staticReviewPageUrl).href;await new Promise((resolveValue,rejectValue)=>{{nextScriptElement.onload=resolveValue;nextScriptElement.onerror=()=>rejectValue(new Error('정적 검수 스크립트를 불러오지 못했습니다.'));document.body.append(nextScriptElement);}});}}
    else{{nextScriptElement.textContent=sourceScriptElement.textContent;document.body.append(nextScriptElement);}}
  }}
  staticReviewRoot.setAttribute('aria-busy','false');
}}catch(currentErrorValue){{staticReviewRoot.setAttribute('aria-busy','false');staticReviewRoot.innerHTML='<p class="static-review-error" role="alert">'+currentErrorValue.message+'</p>';}}
}}"""


def build_static_review_interface(static_review_paths):
    with gr.Blocks(title='정적 검수') as interface_blocks_value:
        gr.Markdown('## 정적 검수\n게임 디자인과 등록 애니메이션을 검수합니다.')
        current_reload_button=gr.Button('검수 화면 새로고침')
        current_reload_button.click(fn=None,js="()=>{window.location.reload();}",queue=False)
        gr.HTML('<section id="static-review-root" aria-label="정적 검수" aria-live="polite" aria-busy="true"><p>검수 화면을 준비하고 있습니다…</p></section>')
    return interface_blocks_value



if __name__=='__main__':
    parser_value=argparse.ArgumentParser()
    parser_value.add_argument('--port',type=int,required=True)
    parser_value.add_argument('--review-port',type=int,required=True)
    parser_value.add_argument('--owner-pid',type=int,required=True)
    parser_value.add_argument('--source-file',type=Path,required=True)
    parser_value.add_argument('--root-path',default='/management/frame/static-review/')
    arguments_value=parser_value.parse_args()
    static_review_paths=load_static_review_paths(arguments_value.source_file)
    def monitor_owner_process():
        while os.getppid()==arguments_value.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_owner_process,daemon=True).start()
    build_static_review_interface(static_review_paths).queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,js=create_static_review_loader(arguments_value.review_port,static_review_paths),allowed_paths=[])
