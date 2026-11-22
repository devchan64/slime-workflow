"""Experimental ROCm adapters; verify numerically before any skin inference."""
import importlib.machinery
import importlib.util
import sys
import types
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[3]
SHIM = ROOT/'.local/trellis-experiment/trellis-strix-halo-2794cbbd05c921876ebff354af5a67f447f5b7a9/runners/trellis/shims.py'


def segment_csr(src, indptr, reduce='sum'):
    if reduce not in ('sum','mean','min','max'):
        raise ValueError('unsupported segment reduction')
    return torch.segment_reduce(src, reduce=reduce, lengths=(indptr[1:]-indptr[:-1]).long())


class CrossMHA(nn.Module):
    """FlashAttention MHA's cross-attention parameter layout, using torch SDPA."""
    def __init__(self, embed_dim, num_heads, cross_attn=True):
        super().__init__()
        if not cross_attn or embed_dim % num_heads:
            raise ValueError('unsupported attention configuration')
        self.num_heads, self.head_dim = num_heads, embed_dim // num_heads
        self.Wq = nn.Linear(embed_dim, embed_dim)
        self.Wkv = nn.Linear(embed_dim, 2*embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)

    def forward(self, x, x_kv):
        b, n, dim = x.shape
        q = self.Wq(x).reshape(b,n,self.num_heads,self.head_dim).transpose(1,2)
        kv = self.Wkv(x_kv).reshape(b,x_kv.shape[1],2,self.num_heads,self.head_dim)
        k = kv[:,:,0].transpose(1,2)
        v = kv[:,:,1].transpose(1,2)
        out = F.scaled_dot_product_attention(q,k,v).transpose(1,2).reshape(b,n,dim)
        return self.out_proj(out)


def install():
    # Load the repository's TRELLIS shim without enabling unrelated replacements.
    spec = importlib.util.spec_from_file_location('unirig_sparse_base', SHIM)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base._install_spconv()
    import spconv.pytorch as spconv
    parent = base._SubMConv3dImpl
    class SubMConv3d(parent):
        def __init__(self, *args, padding=0, **kwargs):
            super().__init__(*args, **kwargs)
    spconv.SubMConv3d = SubMConv3d
    spconv.modules = types.SimpleNamespace(is_spconv_module=lambda obj:isinstance(obj,parent))
    scatter = types.ModuleType('torch_scatter')
    scatter.__spec__ = importlib.machinery.ModuleSpec('torch_scatter',loader=None)
    scatter.segment_csr = segment_csr
    sys.modules['torch_scatter'] = scatter
    flash = types.ModuleType('flash_attn')
    flash.__path__ = []
    flash.__spec__ = importlib.machinery.ModuleSpec('flash_attn',loader=None,is_package=True)
    modules = types.ModuleType('flash_attn.modules')
    modules.__path__ = []
    modules.__spec__ = importlib.machinery.ModuleSpec('flash_attn.modules',loader=None,is_package=True)
    mha = types.ModuleType('flash_attn.modules.mha')
    mha.__spec__ = importlib.machinery.ModuleSpec('flash_attn.modules.mha',loader=None)
    mha.MHA = CrossMHA
    sys.modules.update({'flash_attn':flash,'flash_attn.modules':modules,'flash_attn.modules.mha':mha})
    return base
