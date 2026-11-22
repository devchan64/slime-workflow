"""Check the numerical contracts used by the experimental UniRig adapter."""
import unittest

import torch
from torch.nn import functional as F

from workflow.domains.unirig_experiment.rocm_skin_shims import CrossMHA, install, segment_csr


class UniRigShimTest(unittest.TestCase):
    def test_sparse_convolution_matches_dense_reference(self):
        install()
        import spconv.pytorch as spconv
        torch.manual_seed(12)
        coords = torch.tensor([[0,z,y,x] for z in range(3) for y in range(3) for x in range(3)
                               if (z+y+x)%3 != 0], dtype=torch.int32)
        features = torch.randn(len(coords),2)
        for kernel in (3,5):
            conv = spconv.SubMConv3d(2,3,kernel,padding=1,bias=True)
            with torch.no_grad():
                conv.weight.normal_()
                conv.bias.normal_()
            sparse = spconv.SparseConvTensor(features,coords,[3,3,3],1)
            actual = conv(sparse).features
            dense = F.conv3d(sparse.dense(),conv.weight.permute(0,4,1,2,3),conv.bias,padding=kernel//2)
            i = coords.long()
            expected = dense[i[:,0],:,i[:,1],i[:,2],i[:,3]]
            self.assertTrue(torch.allclose(actual,expected,atol=1e-5,rtol=1e-5))

    def test_segment_reductions(self):
        data = torch.tensor([[1.,4.],[2.,3.],[6.,8.]])
        ptr = torch.tensor([0,2,3])
        self.assertTrue(torch.equal(segment_csr(data,ptr,'max'),torch.tensor([[2.,4.],[6.,8.]])))
        self.assertTrue(torch.equal(segment_csr(data,ptr,'mean'),torch.tensor([[1.5,3.5],[6.,8.]])))

    def test_cross_attention_matches_explicit_attention(self):
        torch.manual_seed(4)
        layer = CrossMHA(8,2)
        q, kv = torch.randn(2,3,8), torch.randn(2,5,8)
        out = layer(q,kv)
        qq = layer.Wq(q).reshape(2,3,2,4).transpose(1,2)
        projected = layer.Wkv(kv).reshape(2,5,2,2,4)
        kk, vv = projected[:,:,0].transpose(1,2), projected[:,:,1].transpose(1,2)
        expected = layer.out_proj((torch.softmax(qq@kk.transpose(-1,-2)/2,dim=-1)@vv).transpose(1,2).reshape(2,3,8))
        self.assertTrue(torch.allclose(out,expected,atol=1e-6,rtol=1e-6))


if __name__ == '__main__':
    unittest.main()
