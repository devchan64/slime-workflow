"""Opt-in diagnostic wrapper for the first Ref2VA attention calls."""
import json,time
from pathlib import Path


def install_attention_trace(attempt,torch,*,max_calls=3):
    from diffusers.models.transformers import transformer_minimax_h3 as h3
    from diffusers.models.attention_dispatch import _AttentionBackendRegistry
    target=Path(attempt); target.mkdir(parents=True,exist_ok=True)
    log=target/'attention-trace.jsonl'; original=h3.dispatch_attention_fn; count=0
    def meta(t):
        return {'shape':list(t.shape),'stride':list(t.stride()),'dtype':str(t.dtype),'device':str(t.device),'contiguous':t.is_contiguous()}
    def emit(row):
        with log.open('a',encoding='utf8') as f:f.write(json.dumps(row,ensure_ascii=False,default=str)+'\n')
    def traced(query,key,value,*args,**kwargs):
        nonlocal count
        count+=1
        if count>max_calls:return original(query,key,value,*args,**kwargs)
        active_name,_=_AttentionBackendRegistry.get_active_backend()
        record={'call':count,'phase':'start','q':meta(query),'k':meta(key),'v':meta(value),'native_sdpa_q_view':meta(query.permute(0,2,1,3)),'native_sdpa_k_view':meta(key.permute(0,2,1,3)),'native_sdpa_v_view':meta(value.permute(0,2,1,3)),'input_layout':'batch,sequence,heads,head_dim','backend_requested':str(kwargs.get('backend')),'diffusers_active_backend':str(active_name),'mask_present':kwargs.get('attn_mask') is not None,'dropout':kwargs.get('dropout_p'),'is_causal':kwargs.get('is_causal'),'measurement':'GPU events with explicit synchronization; diagnostic overhead changes timings','pytorch_sdpa_kernel':'not determined by dispatcher; see optional profiler'}
        emit(record)
        try:
            torch.cuda.synchronize();begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
            profile=None; profile_error=None
            if count==1:
                try:
                    profile=torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA],record_shapes=True)
                    profile.__enter__()
                except Exception as error:
                    profile_error=repr(error);profile=None
            started=time.monotonic();begin.record()
            try: output=original(query,key,value,*args,**kwargs)
            finally:
                end.record();torch.cuda.synchronize()
                if profile is not None:profile.__exit__(None,None,None)
            done={'call':count,'phase':'done','gpu_ms':begin.elapsed_time(end),'wall_ms':(time.monotonic()-started)*1000,'output':meta(output),'profiler_error':profile_error}
            if profile is not None:
                try:
                    trace=target/'attention-first-call.chrome.json.gz';profile.export_chrome_trace(str(trace))
                    done['profiler_trace']=trace.name
                    done['profiler_events']=[{'name':e.key,'device_time_us':getattr(e,'self_device_time_total',None),'count':e.count} for e in profile.key_averages() if getattr(e,'self_device_time_total',0)>0]
                except Exception as error:done['profiler_export_error']=repr(error)
            emit(done);return output
        except BaseException as error:
            emit({'call':count,'phase':'error','error':repr(error)});raise
    h3.dispatch_attention_fn=traced
    return log
