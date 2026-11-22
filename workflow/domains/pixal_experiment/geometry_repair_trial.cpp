#include "remesh_dc.h"
#include "tri_bvh.h"
#include "uv_bake.h"
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <cstdint>
int main(int argc,char** argv){
 if(argc!=4)return 2; FILE* in=fopen(argv[1],"rb"); if(!in)return 3; int32_t v=0,f=0; if(fread(&v,4,1,in)!=1||fread(&f,4,1,in)!=1||v<=0||f<=0)return 4;
 std::vector<float> verts((size_t)v*3); std::vector<int32_t> faces((size_t)f*3); if(fread(verts.data(),4,verts.size(),in)!=verts.size()||fread(faces.data(),4,faces.size(),in)!=faces.size())return 5; fclose(in);
 fprintf(stderr,"input V=%d F=%d\n",v,f); auto welded=trellis::weld_vertices(verts,faces,nullptr,1.0f/(1024*8)); auto filled=trellis::fill_holes(verts,faces,0.03f); fprintf(stderr,"weld=%d holes=%d V=%zu F=%zu\n",welded,filled,verts.size()/3,faces.size()/3);
 auto bvh=trellis::TriBvh::build(verts.data(),verts.size()/3,faces.data(),faces.size()/3); auto mesh=trellis::remesh_narrow_band_dc(verts.data(),verts.size()/3,faces.data(),faces.size()/3,bvh,1024,1); if(mesh.F()==0)return 6; trellis::clean_mesh(mesh.V(),mesh.faces); fprintf(stderr,"remesh V=%d F=%d\n",mesh.V(),mesh.F());
 std::vector<float> outv; std::vector<int32_t> outf; trellis::decimate_qem_cpu(mesh.verts,mesh.V(),mesh.faces,mesh.F(),atoi(argv[3]),outv,outf); if(outf.empty())return 7; fprintf(stderr,"decimated V=%zu F=%zu\n",outv.size()/3,outf.size()/3);
 FILE* out=fopen(argv[2],"wb"); if(!out)return 8; int32_t nv=outv.size()/3,nf=outf.size()/3; fwrite(&nv,4,1,out); fwrite(&nf,4,1,out); fwrite(outv.data(),4,outv.size(),out); fwrite(outf.data(),4,outf.size(),out); fclose(out); return 0;
}
