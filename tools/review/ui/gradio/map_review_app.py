"""마을 맵 검수 정적 구성 요소를 Gradio 작업 영역에서 실행한다."""
import argparse
import json
import threading
import time

import gradio as gr


MAP_REVIEW_APPLICATION_STYLES='#map-review-root{min-height:0}.gradio-container{max-width:none!important;padding:8px!important}.map-review-error{padding:16px;border:1px solid #9c4b4b;border-radius:8px;color:#ffd3d3}'


def create_map_review_loader(review_server_port):
    review_page_url=f'http://127.0.0.1:{review_server_port}/isloon-map-review/map-review.html?embedded=1'
    serialized_page_url=json.dumps(review_page_url)
    return f"""async()=>{{
const mapReviewRoot=document.querySelector('#map-review-root');
if(!mapReviewRoot||mapReviewRoot.dataset.mapReviewLoaded)return;
mapReviewRoot.dataset.mapReviewLoaded='true';
const mapReviewPageUrl={serialized_page_url};
const mapReviewAssetUrl=new URL('.',mapReviewPageUrl).href;
const originalFetchRequest=window.fetch.bind(window);
window.fetch=(requestValue,...requestOptionValues)=>{{
  if(typeof requestValue==='string'&&!/^(?:[a-z]+:|\\/)/i.test(requestValue))return originalFetchRequest(new URL(requestValue,mapReviewAssetUrl),...requestOptionValues);
  return originalFetchRequest(requestValue,...requestOptionValues);
}};
try{{
  const mapReviewResponse=await originalFetchRequest(mapReviewPageUrl,{{cache:'no-store'}});
  if(!mapReviewResponse.ok)throw new Error('맵 검수 화면을 불러오지 못했습니다.');
  const mapReviewDocument=new DOMParser().parseFromString(await mapReviewResponse.text(),'text/html');
  for(const sourceStyleElement of mapReviewDocument.querySelectorAll('style')){{
    const nextStyleElement=document.createElement('style');nextStyleElement.dataset.mapReviewComponent='true';nextStyleElement.textContent=sourceStyleElement.textContent;document.head.append(nextStyleElement);
  }}
  for(const sourceLinkElement of mapReviewDocument.querySelectorAll('link[rel="stylesheet"]')){{
    const nextLinkElement=document.createElement('link');nextLinkElement.rel='stylesheet';nextLinkElement.href=new URL(sourceLinkElement.getAttribute('href'),mapReviewPageUrl).href;nextLinkElement.dataset.mapReviewComponent='true';document.head.append(nextLinkElement);
  }}
  const mapReviewMarkup=[...mapReviewDocument.body.children].filter(currentElementValue=>currentElementValue.tagName!=='SCRIPT').map(currentElementValue=>currentElementValue.outerHTML).join('');
  mapReviewRoot.innerHTML=mapReviewMarkup;
  for(const sourceScriptElement of mapReviewDocument.querySelectorAll('script')){{
    const nextScriptElement=document.createElement('script');nextScriptElement.dataset.mapReviewComponent='true';
    if(sourceScriptElement.type)nextScriptElement.type=sourceScriptElement.type;
    if(sourceScriptElement.src){{nextScriptElement.src=new URL(sourceScriptElement.getAttribute('src'),mapReviewPageUrl).href;await new Promise((resolveValue,rejectValue)=>{{nextScriptElement.onload=resolveValue;nextScriptElement.onerror=()=>rejectValue(new Error('맵 검수 스크립트를 불러오지 못했습니다.'));document.body.append(nextScriptElement);}});}}
    else{{nextScriptElement.textContent=sourceScriptElement.textContent;document.body.append(nextScriptElement);}}
  }}
}}catch(currentErrorValue){{mapReviewRoot.innerHTML='<p class="map-review-error" role="alert">'+currentErrorValue.message+'</p>';}}
}}"""


def build_map_review_interface(review_server_port):
    with gr.Blocks(title='마을 맵 검수') as interface_blocks_value:
        gr.HTML('<section id="map-review-root" aria-label="마을 맵 검수"><p>맵 검수 화면을 준비하고 있습니다…</p></section>')
    return interface_blocks_value


from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/management/frame/map-review/');arguments_value=parser_value.parse_args()
    threading.Thread(target=lambda:time.sleep(1),daemon=True).start();build_map_review_interface(arguments_value.review_port).queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,css=MAP_REVIEW_APPLICATION_STYLES+MANAGEMENT_DENSITY_STYLES,js=create_map_review_loader(arguments_value.review_port),allowed_paths=[])
