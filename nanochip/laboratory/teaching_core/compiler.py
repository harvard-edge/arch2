"""Shape-derived scalar microcode for the complete frozen integer workload.

No weight, token, activation, routing decision, or golden is inspected by this
compiler. Descriptor offsets derive solely from the canonical tensor shapes.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import math
import struct
from .contract import CONFIG, TeachingConfig
from .isa import Op, encode, program_bytes, DATA_BASE, TABLE_BASE
from .compiler_layout import tensor_layout

@dataclass
class CompiledProgram:
    program: bytes
    tables: bytes
    required_words: int
    manifest: dict
    @property
    def instructions(self):
        return [int.from_bytes(self.program[i:i+16],'little') for i in range(0,len(self.program),16)]
    @property
    def scratch_words(self): return self.required_words
    @property
    def table_regions(self): return self.manifest['table_regions']
    @property
    def scratch_map(self): return self.manifest['scratch_map']
    @property
    def token_count(self): return self.manifest['token_count']


class Builder:
    def __init__(self,c,seq_len):
        self.c=c; self.seq_len=seq_len; self.code=[]; self.observations=[]; self.labels={}; self.fixups=[]; self.calls=[]
        self.label_counter=0; self.cursor=0; self.high=0; self.regions={}; self.tables=bytearray(); self.table_regions={}
        self.entries,self.mats=tensor_layout(c)
        self.desc={nm:256+16*i+4 for i,(nm,_,_) in enumerate(self.entries)}
        self.types=c.layer_pattern*(c.n_layers//len(c.layer_pattern))
        self.state={}
        for i,t in enumerate(self.types):
            if t=='L':
                self.state[i]=(self.alloc(c.kda_heads*c.kda_dim*c.kda_dim,f'L{i}.state'), self.alloc(3*(c.conv_kernel-1)*c.kda_heads*c.kda_dim,f'L{i}.history'))
            else:
                self.state[i]=(self.alloc(c.max_seq*c.n_heads*(c.mla_dk+c.mla_dr),f'L{i}.keys'),self.alloc(c.max_seq*c.n_heads*c.mla_dv,f'L{i}.values'))
        self.position=self.alloc(1,"token_position")[0]
        self.persistent_end=self.cursor
        rom=Path(__file__).resolve().parents[2]/'kpu/rtl/roms'
        widths={'sigmoid':20,'alpha':20,'expneg':20,'rsqrt':16,'recip':16}
        for nm in widths:
            for delta in (False,True):
                name=nm+('_d' if delta else ''); path=rom/(name+'.hex')
                vals=[int(s,16) for s in path.read_text().split()]
                if delta:
                    bits=widths[nm]; vals=[v-(1<<bits) if v&(1<<(bits-1)) else v for v in vals]
                base=TABLE_BASE+len(self.tables)
                self.table_regions[name]={'address':base,'entries':len(vals),'signed':delta,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                self.tables.extend(b''.join(struct.pack('<q',v) for v in vals))
    def alloc(self,n,name=None):
        a=list(range(self.cursor,self.cursor+n)); self.cursor+=n; self.high=max(self.high,self.cursor)
        if name: self.regions[name]={'start':a[0],'words':n}
        return a
    def emit(self,op,rd=0,ra=0,rb=0,imm=0,flags=0): self.code.append([op,rd,ra,rb,imm,flags])
    def label(self,name=None):
        name=name or f'label{len(self.labels)}'; self.labels[name]=len(self.code); return name
    def new(self):
        self.label_counter+=1
        return f'future{self.label_counter}'
    def jump(self,label,reg=None):
        self.fixups.append((len(self.code),label)); self.emit(Op.JMP if reg is None else Op.JZ,ra=reg or 0)
    def li(self,r,v): self.emit(Op.LI,r,imm=v)
    def mov(self,d,a): self.li(11,0); self.emit(Op.ADD,d,a,11)
    def op(self,op,d,a,b): self.emit(op,d,a,b)
    def const(self,op,d,a,v): self.li(11,v); self.op(op,d,a,11)
    def rs(self,r,n):
        if n>0: self.const(Op.ADD,r,r,1<<(n-1)); self.const(Op.ASR,r,r,n)
        elif n<0: self.const(Op.SHL,r,r,-n)
    def ld(self,r,a): self.li(11,0); self.emit(Op.LDS,r,11,imm=a)
    def st(self,a,r): self.li(11,0); self.emit(Op.STS,ra=11,rb=r,imm=a)
    def load64(self,r,a):
        self.ld(r,a); self.const(Op.AND,r,r,0xffffffff); self.ld(10,a+1); self.const(Op.SHL,10,10,32); self.op(Op.OR,r,r,10)
    def store64(self,a,r): self.st(a,r); self.const(Op.ASR,10,r,32); self.st(a+1,10)
    def satst(self,a,r=0): self.emit(Op.SAT32,r,r); self.st(a,r)
    def ext(self,r,addr,width=2,signed=True,base=None):
        if base is None: self.li(11,0); base=11
        self.emit(Op.LDX,r,base,imm=addr,flags={1:0,2:1,4:2,8:3}[width]|(4 if signed else 0))
    def ptr(self,r,name): self.ext(r,DATA_BASE+self.desc[name],4,False); self.const(Op.ADD,r,r,DATA_BASE)
    def param(self,r,name,i=0): self.ptr(9,name); self.ext(r,i*2,base=9)
    def call(self,name):
        label=self.new(); ident=len(self.calls); self.calls.append(label)
        self.li(15,ident); self.jump(name); self.label(label)
    def table(self,nm,idx,out):
        self.const(Op.SHL,9,idx,3); self.ext(out,self.table_regions[nm]['address'],8,True,base=9)
    def clip(self,r,lo,hi):
        done=self.new(); self.li(8,lo); self.op(Op.LT,7,r,8); self.jump(done,7); self.mov(r,8); self.label(done)
        done=self.new(); self.li(8,hi); self.op(Op.LT,7,8,r); self.jump(done,7); self.mov(r,8); self.label(done)
    def observe(self,name,words,fraction_bits=26):
        self.observations.append({"pc":len(self.code),"name":name,"words":list(words),"fraction_bits":fraction_bits})
    def copy(self,x):
        out=self.alloc(len(x))
        for a,b in zip(x,out): self.ld(0,a); self.st(b,0)
        return out
    def gemv(self,nm,x,shift=12):
        k,n=self.mats[nm]; out=self.alloc(n); g=min(self.c.group_size,k)
        self.ptr(8,nm+'.q'); self.ptr(9,nm+'.s'); self.ptr(10,nm+'.z')
        self.li(12,0); begin=self.label(); self.li(13,0)
        for start in range(0,k,g):
            self.li(14,0)
            for j in range(start,min(start+g,k)):
                # Output column is runtime; base pointers stay in r8..r10.
                self.op(Op.ADD,6,8,12); self.ext(0,(j//2)*n,1,False,base=6)
                if j%2: self.const(Op.ASR,0,0,4)
                self.const(Op.AND,0,0,15)
                self.op(Op.ADD,6,10,12); self.ext(1,(start//g)*n,1,False,base=6)
                self.op(Op.SUB,0,0,1); self.ld(1,x[j]); self.op(Op.MUL,0,0,1); self.op(Op.ADD,14,14,0)
            self.const(Op.SHL,6,12,1); self.op(Op.ADD,6,9,6); self.ext(0,(start//g)*n*2,2,True,base=6)
            self.op(Op.MUL,0,0,14); self.op(Op.ADD,13,13,0)
        self.mov(0,13); self.rs(0,shift); self.emit(Op.SAT32,0,0)
        self.li(11,out[0]); self.op(Op.ADD,11,11,12); self.emit(Op.STS,ra=11,rb=0)
        self.const(Op.ADD,12,12,1); self.li(11,n); self.op(Op.LT,0,12,11); end=self.new(); self.jump(end,0); self.jump(begin); self.label(end)
        return out
    def norm(self,x,name=None):
        out=self.alloc(len(x)); self.li(0,0)
        for a in x: self.ld(1,a); self.op(Op.MUL,1,1,1); self.op(Op.ADD,0,0,1)
        if name:
            self.const(Op.MUL,0,0,round((1<<24)/len(x))); self.rs(0,44); eps=round(1e-5*(1<<32))
        else: self.rs(0,20); eps=round(1e-6*(1<<32))
        self.const(Op.ADD,0,0,eps); self.call('rsqrt'); self.mov(14,0)
        for i,(a,b) in enumerate(zip(x,out)):
            if name:
                self.param(1,name,i); self.const(Op.ADD,1,1,8192); self.op(Op.MUL,1,1,14); self.rs(1,13)
            else: self.mov(1,14)
            self.ld(0,a); self.rs(0,4); self.op(Op.MUL,0,0,1); self.rs(0,20); self.satst(b)
        return out
    def nonlinear(self,x,kind='sigmoid',silu=False):
        out=self.alloc(len(x))
        for a,b in zip(x,out):
            self.ld(0,a); self.li(1,18); self.call(kind)
            if silu: self.ld(1,a); self.op(Op.MUL,0,0,1); self.rs(0,26); self.emit(Op.SAT32,0,0)
            self.st(b,0)
        return out
    def softmix(self,logs,cands,mla=False):
        out=self.alloc(len(cands[0])); mark=self.cursor; es=self.alloc(len(logs))
        self.load64(14,logs[0])
        for a in logs[1:]:
            self.load64(0,a); self.op(Op.LT,1,14,0); done=self.new(); self.jump(done,1); self.mov(14,0); self.label(done)
        # Keep max across LUT calls in scratch64.
        mx=self.alloc(2)[0]; self.store64(mx,14)
        for t,(a,b) in enumerate(zip(logs,es)):
            skip=done=None
            if mla:
                self.ld(0,self.position); self.li(1,t); self.op(Op.LT,0,0,1); skip=self.new(); done=self.new(); self.jump(skip,0); self.li(0,0); self.st(b,0); self.jump(done); self.label(skip)
            self.load64(0,a); self.load64(1,mx); self.op(Op.SUB,0,0,1)
            if not mla: self.rs(0,11)
            self.clip(0,-(1<<30),0); self.li(1,18); self.call('expneg'); self.st(b,0)
            if mla: self.label(done)
        self.li(0,0)
        for a in es: self.ld(1,a); self.op(Op.ADD,0,0,1)
        self.call('recip'); self.mov(14,0)
        for j,b in enumerate(out):
            self.li(0,0)
            for a,cd in zip(es,cands):
                self.ld(1,a)
                if mla: self.rs(1,4)
                self.ld(2,cd[j]); self.op(Op.MUL,1,1,2); self.op(Op.ADD,0,0,1)
            self.rs(0,28 if mla else 24); self.op(Op.MUL,0,0,14); self.rs(0,14 if mla else 22); self.satst(b)
        self.cursor=mark; return out
    def resmix(self,prefix,blocks,name):
        out=self.alloc(len(prefix)); mark=self.cursor; logs=[]; cands=blocks+[prefix]
        for cd in cands:
            vn=self.norm(cd,name+'.norm.w'); a=self.alloc(2)[0]; logs.append(a); self.li(0,0)
            for i,v in enumerate(vn): self.ld(1,v); self.param(2,name+'.proj',i); self.op(Op.MUL,1,1,2); self.op(Op.ADD,0,0,1)
            self.store64(a,0)
        mix=self.softmix(logs,cands)
        for a,b in zip(mix,out): self.ld(0,a); self.st(b,0)
        self.cursor=mark; return out
    def swiglu(self,h,p):
        out=self.alloc(self.c.d_model); mark=self.cursor
        g=self.gemv(p+'g',h); u=self.gemv(p+'u',h); sg=self.nonlinear(g,silu=True)
        for a,b in zip(sg,u): self.ld(0,a); self.ld(1,b); self.op(Op.MUL,0,0,1); self.rs(0,26); self.satst(a)
        d=self.gemv(p+'d',sg)
        for a,b in zip(d,out): self.ld(0,a); self.st(b,0)
        self.cursor=mark; return out
    def moe(self,li,h):
        c=self.c; p=f'L{li}.moe.'; out=self.alloc(c.d_model); mark=self.cursor
        rin=self.gemv(p+'router',h); scores=self.nonlinear(rin); metrics=self.alloc(2*c.n_experts); selected=self.alloc(c.top_k); weights=self.alloc(c.top_k)
        for i,a in enumerate(scores): self.ld(0,a); self.param(1,p+'bias',i); self.const(Op.SHL,1,1,15); self.op(Op.ADD,0,0,1); self.store64(metrics[2*i],0)
        for dest in selected:
            self.load64(12,metrics[0]); self.li(13,0)
            for j in range(1,c.n_experts):
                self.load64(0,metrics[2*j]); self.op(Op.LT,1,12,0); end=self.new(); self.jump(end,1); self.mov(12,0); self.li(13,j); self.label(end)
            self.st(dest,13); self.const(Op.SHL,0,13,1); self.const(Op.ADD,0,0,metrics[0]); self.li(1,0); self.emit(Op.STS,ra=0,rb=1); self.const(Op.ADD,0,0,1); self.li(1,-(1<<30)); self.emit(Op.STS,ra=0,rb=1)
        self.li(14,0)
        for a in selected: self.ld(0,a); self.const(Op.ADD,0,0,scores[0]); self.emit(Op.LDS,1,0); self.op(Op.ADD,14,14,1)
        summ=self.alloc(2)[0]; self.store64(summ,14)
        for a,b in zip(selected,weights):
            self.ld(0,a); self.const(Op.ADD,0,0,scores[0]); self.emit(Op.LDS,0,0); self.const(Op.MUL,0,0,round(2.828*(1<<26))); self.load64(1,summ); self.const(Op.ASR,2,1,1); self.op(Op.ADD,0,0,2); self.call('divide'); self.emit(Op.SAT32,0,0); self.st(b,0)
        self.observe(f'L{li}.moe_indices',selected,0); self.observe(f'L{li}.moe_weights',weights,26)
        shared=self.swiglu(h,p+'shared.'); acc=self.alloc(2*c.d_model)
        for j,a in enumerate(shared): self.ld(0,a); self.store64(acc[2*j],0)
        for sel,wt in zip(selected,weights):
            done=self.new()
            for expert in range(c.n_experts):
                self.ld(0,sel); self.li(1,expert); self.op(Op.EQ,0,0,1); skip=self.new(); self.jump(skip,0)
                e=self.swiglu(h,p+f'e{expert}.')
                for j,a in enumerate(e):
                    self.ld(0,a); self.ld(1,wt); self.op(Op.MUL,0,0,1); self.rs(0,26); self.load64(1,acc[2*j]); self.op(Op.ADD,0,0,1); self.store64(acc[2*j],0)
                self.jump(done); self.label(skip)
                self.cursor=e[0]
            self.label(done)
        for j,b in enumerate(out): self.load64(0,acc[2*j]); self.satst(b)
        self.cursor=mark; return out
    def conv(self,li,stream,x):
        c=self.c; P=c.kda_heads*c.kda_dim; K=c.conv_kernel; p=f'L{li}.kda.'; hist=self.state[li][1]; out=self.alloc(P)
        for j,b in enumerate(out):
            self.li(0,0)
            for t in range(K):
                self.ld(1,x[j] if t==K-1 else hist[(stream*(K-1)+t)*P+j]); self.param(2,p+'qkv'[stream]+'conv',j*K+t); self.op(Op.MUL,1,1,2); self.op(Op.ADD,0,0,1)
            # Preserve Q37 sum through interpolation.
            tmp=self.alloc(2)[0]; self.store64(tmp,0); self.li(1,29); self.call('sigmoid'); self.load64(1,tmp); self.rs(1,16); self.op(Op.MUL,0,0,1); self.rs(0,21); self.satst(b); self.cursor=tmp
        for t in range(K-1):
            for j in range(P):
                self.ld(0,x[j] if t==K-2 else hist[(stream*(K-1)+t+1)*P+j]); self.st(hist[(stream*(K-1)+t)*P+j],0)
        return out
    def kda(self,li,h):
        c=self.c; H=c.kda_heads; d=c.kda_dim; P=H*d; p=f'L{li}.kda.'
        out=self.alloc(c.d_model); mark=self.cursor
        streams=[]
        for s,nm in enumerate('qkv'): streams.append(self.conv(li,s,self.gemv(p+nm,h)))
        q,k,v=streams
        beta=self.nonlinear(self.gemv(p+'b',h)); f=self.gemv(p+'f2',self.gemv(p+'f1',h)); alpha=self.alloc(P)
        for j,b in enumerate(alpha):
            self.ld(0,f[j]); self.param(1,p+'dtb',j); self.const(Op.SHL,1,1,15); self.op(Op.ADD,0,0,1); self.param(1,p+'A',j//d); self.op(Op.MUL,0,0,1); self.rs(0,8); self.li(1,18); self.call('alpha'); self.st(b,0)
        z=self.nonlinear(self.gemv(p+'g2',self.gemv(p+'g1',h))); core=self.alloc(P); S=self.state[li][0]
        for hd in range(H):
            hmark=self.cursor; qh=self.norm(q[hd*d:(hd+1)*d]); kh=self.norm(k[hd*d:(hd+1)*d]); Sd=self.alloc(d*d); u=self.alloc(2*d); bk=self.alloc(d); o=self.alloc(d)
            for i in range(d):
                for j in range(d):
                    self.ld(0,S[(hd*d+i)*d+j]); self.ld(1,alpha[hd*d+i]); self.op(Op.MUL,0,0,1); self.rs(0,26); self.st(Sd[i*d+j],0)
            for j in range(d):
                self.li(0,0)
                for i in range(d):
                    self.ld(1,Sd[i*d+j]); self.rs(1,4); self.ld(2,kh[i]); self.op(Op.MUL,1,1,2); self.op(Op.ADD,0,0,1)
                self.rs(0,22); self.ld(1,v[hd*d+j]); self.const(Op.SHL,1,1,1); self.op(Op.SUB,0,1,0); self.store64(u[2*j],0)
            for i in range(d):
                self.ld(0,beta[hd]); self.ld(1,kh[i]); self.op(Op.MUL,0,0,1); self.rs(0,24); self.st(bk[i],0)
                for j in range(d):
                    self.ld(0,bk[i]); self.load64(1,u[2*j]); self.op(Op.MUL,0,0,1); self.rs(0,28); self.ld(1,Sd[i*d+j]); self.op(Op.ADD,0,0,1); self.satst(S[(hd*d+i)*d+j])
            for j in range(d):
                self.li(0,0)
                for i in range(d):
                    self.ld(1,S[(hd*d+i)*d+j]); self.rs(1,4); self.ld(2,qh[i]); self.op(Op.MUL,1,1,2); self.op(Op.ADD,0,0,1)
                self.rs(0,23); self.const(Op.MUL,0,0,round((1<<16)/math.sqrt(d))); self.rs(0,16); self.satst(o[j])
            on=self.norm(o,p+'onorm.w')
            for j in range(d): self.ld(0,on[j]); self.ld(1,z[hd*d+j]); self.op(Op.MUL,0,0,1); self.rs(0,26); self.satst(core[hd*d+j])
            self.cursor=hmark
        self.observe(f'L{li}.kda_core',core); self.observe(f'L{li}.kda_state',S,27)
        y=self.gemv(p+'o',core)
        for a,b in zip(y,out): self.ld(0,a); self.st(b,0)
        self.cursor=mark; return out
    def mla(self,li,h,pos=None):
        c=self.c; p=f'L{li}.mla.'; H=c.n_heads; dk=c.mla_dk; dr=c.mla_dr; dv=c.mla_dv; dq=dk+dr
        out=self.alloc(c.d_model); mark=self.cursor
        lat=self.norm(self.gemv(p+'wc',h),p+'knorm.w'); qc=self.gemv(p+'wq_c',h); qr=self.gemv(p+'wq_r',h); kc=self.gemv(p+'wk_c',lat); kr=self.gemv(p+'wk_r',h); vv=self.gemv(p+'wv',lat)
        q=self.alloc(H*dq); K,V=self.state[li]
        for hd in range(H):
            for j in range(dq):
                self.ld(0,qc[hd*dk+j] if j<dk else qr[hd*dr+j-dk]); self.st(q[hd*dq+j],0)
                self.ld(0,kc[hd*dk+j] if j<dk else kr[j-dk]); self.ld(1,self.position); self.const(Op.MUL,1,1,H*dq); self.const(Op.ADD,1,1,K[hd*dq+j]); self.emit(Op.STS,ra=1,rb=0)
            for j in range(dv): self.ld(0,vv[hd*dv+j]); self.ld(1,self.position); self.const(Op.MUL,1,1,H*dv); self.const(Op.ADD,1,1,V[hd*dv+j]); self.emit(Op.STS,ra=1,rb=0)
        ctx=self.alloc(H*dv)
        for hd in range(H):
            hmark=self.cursor; logs=[]; cands=[]
            for t in range(c.max_seq):
                a=self.alloc(2)[0]; logs.append(a); self.li(0,0)
                for j in range(dq):
                    self.ld(1,K[(t*H+hd)*dq+j]); self.rs(1,4); self.ld(2,q[hd*dq+j]); self.rs(2,4); self.op(Op.MUL,1,1,2); self.op(Op.ADD,0,0,1)
                self.rs(0,18); self.const(Op.MUL,0,0,round((1<<16)/math.sqrt(dq))); self.rs(0,16); self.ld(1,self.position); self.li(2,t); self.op(Op.LT,1,1,2); valid=self.new(); self.jump(valid,1); self.li(0,-(1<<62)); self.label(valid); self.store64(a,0)
                cands.append(V[(t*H+hd)*dv:(t*H+hd+1)*dv])
            y=self.softmix(logs,cands,mla=True)
            for j,a in enumerate(y): self.ld(0,a); self.st(ctx[hd*dv+j],0)
            self.cursor=hmark
        self.observe(f'L{li}.mla_ctx',ctx)
        y=self.gemv(p+'o',ctx)
        for a,b in zip(y,out): self.ld(0,a); self.st(b,0)
        self.cursor=mark; return out
    def embedding(self,pos=None):
        c=self.c; out=self.alloc(c.d_model); self.ext(12,DATA_BASE+24*4,4,False); self.ld(0,self.position); self.const(Op.SHL,0,0,2); self.op(Op.ADD,12,12,0); self.ext(12,DATA_BASE,4,False,base=12)
        g=min(c.group_size,c.d_model); ng=(c.d_model+g-1)//g
        self.ptr(8,'emb.q'); self.const(Op.MUL,0,12,c.d_model//2); self.op(Op.ADD,8,8,0)
        self.ptr(9,'emb.s'); self.const(Op.MUL,0,12,ng*2); self.op(Op.ADD,9,9,0)
        self.ptr(10,'emb.z'); self.const(Op.MUL,0,12,ng); self.op(Op.ADD,10,10,0)
        for j,b in enumerate(out):
            self.ext(0,j//2,1,False,base=8)
            if j%2: self.const(Op.ASR,0,0,4)
            self.const(Op.AND,0,0,15); self.ext(1,j//g,1,False,base=10); self.op(Op.SUB,0,0,1); self.ext(1,(j//g)*2,2,True,base=9); self.op(Op.MUL,0,0,1); self.rs(0,-14); self.satst(b)
        return out
    def build(self):
        c=self.c
        self.li(0,0)
        for a in range(self.persistent_end): self.st(a,0)
        for pos in [None]:
            token_loop=self.label()
            self.cursor=self.persistent_end; x=self.embedding(pos); blocks=[]
            for li,t in enumerate(self.types):
                boundary=li%c.attn_res_block==0; prefix=x
                if boundary: blocks.append(x)
                mix_in=blocks[:-1] if boundary else blocks
                if mix_in: x=self.resmix(x,mix_in,f'L{li}.res_attn')
                h1=self.norm(x,f'L{li}.norm1.w'); a=self.kda(li,h1) if t=='L' else self.mla(li,h1,pos)
                if boundary: prefix=a
                else:
                    out=self.alloc(c.d_model)
                    for aa,bb,dd in zip(prefix,a,out): self.ld(0,aa); self.ld(1,bb); self.op(Op.ADD,0,0,1); self.satst(dd)
                    prefix=out
                x=self.resmix(prefix,blocks,f'L{li}.res_mlp'); h2=self.norm(x,f'L{li}.norm2.w'); m=self.moe(li,h2); x=self.alloc(c.d_model)
                for aa,bb,dd in zip(prefix,m,x): self.ld(0,aa); self.ld(1,bb); self.op(Op.ADD,0,0,1); self.satst(dd)
                self.observe(f'L{li}.layer_out',x)
            x=self.resmix(x,blocks,'res_out'); hn=self.norm(x,'final_norm.w'); logits=self.gemv('head',hn,10)
            self.ext(12,DATA_BASE+25*4,4,False); self.ext(13,DATA_BASE+30*4,4,False); self.ld(0,self.position); self.op(Op.MUL,13,13,0); self.op(Op.ADD,12,12,13); self.const(Op.ADD,12,12,DATA_BASE)
            self.li(14,-(1<<31)); self.li(13,0)
            for j,a in enumerate(logits):
                self.ld(0,a); self.emit(Op.STX,ra=12,rb=0,imm=j*4); self.op(Op.LT,1,14,0); skip=self.new(); self.jump(skip,1); self.mov(14,0); self.li(13,j); self.label(skip)
            self.ext(12,DATA_BASE+26*4,4,False); self.ld(0,self.position); self.const(Op.SHL,0,0,2); self.op(Op.ADD,12,12,0); self.const(Op.ADD,12,12,DATA_BASE); self.emit(Op.STX,ra=12,rb=13)
            self.ld(0,self.position); self.const(Op.ADD,0,0,1); self.st(self.position,0); self.li(1,self.seq_len); self.op(Op.LT,0,0,1); tokens_done=self.new(); self.jump(tokens_done,0); self.jump(token_loop); self.label(tokens_done)
        self.ext(12,DATA_BASE+27*4,4,False); self.const(Op.ADD,12,12,DATA_BASE); self.li(0,0x600DD00D); self.emit(Op.STX,ra=12,rb=0); self.emit(Op.HALT)
        self.helpers()
        for index,label in self.fixups: self.code[index][4]=self.labels[label]
        instr=tuple(encode(op,rd,ra,rb,imm,flags) for op,rd,ra,rb,imm,flags in self.code)
        program=program_bytes(instr)
        if len(program)>DATA_BASE: raise ValueError(f'Program overlaps data: {len(program)} bytes')
        if self.high>1024: raise ValueError(f'Static scratch overflow: {self.high}')
        manifest={'schema':'nanochip-teaching-microcode/v0','configuration':asdict(c),'token_count':self.seq_len,'instruction_count':len(instr),'program_bytes':len(program),'data_base':DATA_BASE,'table_base':TABLE_BASE,'table_regions':self.table_regions,'observations':self.observations,'scratch_map':self.regions,'static_high_water_words':self.high,'minimum_power_of_two_words':1<<(self.high-1).bit_length(),'scratch_words':self.high,'source_semantics':'frozen kpu/rtl/selfmodel/fxmodel.py','program_sha256':hashlib.sha256(program).hexdigest(),'tables_sha256':hashlib.sha256(self.tables).hexdigest(),'specialization_inputs':['configuration','token_count'],'runtime_inputs':['packed tensor descriptors','packed weights and parameters','tokens'],'all_scratch_reads_checked_by_interpreter':True,'tensor_descriptors':[{'name':nm,'descriptor_address':DATA_BASE+256+16*i,'packed_bytes':size} for i,(nm,size,_) in enumerate(self.entries)]}
        return CompiledProgram(program,bytes(self.tables),self.high,manifest)
    def helpers(self):
        for name,n,offset in [('sigmoid',8192,4096),('alpha',8192,4096),('expneg',4096,4096)]:
            self.label(name)
            # r0=input, r1=domain_frac-8; floor bucket and full fraction.
            self.op(Op.ASR,2,0,1); self.op(Op.SHL,3,2,1); self.op(Op.SUB,3,0,3); self.const(Op.ADD,4,2,offset); self.clip(4,0,n)
            self.table(name,4,5); self.table(name+'_d',4,6); self.op(Op.MUL,6,6,3)
            self.const(Op.SUB,2,1,1); self.li(3,1); self.op(Op.SHL,3,3,2); self.op(Op.ADD,6,6,3); self.op(Op.ASR,6,6,1); self.op(Op.ADD,0,5,6); self.jump('return_dispatch')
        for name in ['rsqrt','recip']:
            self.label(name)
            # Positive integer normalization to [2^20,2^21); E9 starts at9.
            self.mov(2,0); self.li(3,9)
            loop=self.label(); end=self.new(); self.li(4,1<<21); self.op(Op.LT,5,2,4); self.jump(end,5); down=self.new(); self.jump(down); self.label(end)
            self.const(Op.ASR,2,2,1); self.const(Op.ADD,3,3,1); self.jump(loop); self.label(down)
            loop=self.label(); self.li(4,1<<20); self.op(Op.LT,5,2,4); end=self.new(); self.jump(end,5); self.const(Op.SHL,2,2,1); self.const(Op.SUB,3,3,1); self.jump(loop); self.label(end)
            self.const(Op.ASR,4,2,9); self.const(Op.SUB,4,4,2048); self.const(Op.AND,2,2,511)
            self.table(name,4,5); self.table(name+'_d',4,6); self.op(Op.MUL,6,6,2); self.rs(6,9); self.op(Op.ADD,0,5,6)
            if name=='rsqrt':
                self.const(Op.AND,4,3,1); skip=self.new(); self.jump(skip,4); self.const(Op.MUL,0,0,370728); self.rs(0,18); self.const(Op.ADD,3,3,1); self.label(skip)
                self.const(Op.ASR,3,3,1); self.li(4,8); self.op(Op.SUB,3,4,3)
            else:
                self.li(4,16); self.op(Op.SUB,3,4,3)
            self.li(4,0); self.op(Op.LT,5,3,4); right=self.new(); done=self.new(); self.jump(right,5)
            self.op(Op.SUB,3,4,3); self.const(Op.SUB,4,3,1); self.li(5,1); self.op(Op.SHL,5,5,4); self.op(Op.ADD,0,0,5); self.op(Op.ASR,0,0,3); self.jump(done)
            self.label(right); self.op(Op.SHL,0,0,3); self.label(done); self.jump('return_dispatch')
        self.label('divide')
        # Unsigned positive quotient; 64-bit restoring division. Numerator<2^63.
        self.mov(2,0); self.li(0,0); self.li(3,0); self.li(4,63)
        loop=self.label(); self.const(Op.SHL,3,3,1); self.op(Op.ASR,5,2,4); self.const(Op.AND,5,5,1); self.op(Op.OR,3,3,5); self.op(Op.LT,6,3,1); use=self.new(); skip=self.new(); self.jump(use,6); self.jump(skip)
        self.label(use); self.op(Op.SUB,3,3,1); self.li(5,1); self.op(Op.SHL,5,5,4); self.op(Op.OR,0,0,5); self.label(skip); self.const(Op.SUB,4,4,1); self.li(5,0); self.op(Op.LT,6,4,5); end=self.new(); self.jump(loop,6); self.label(end); self.jump('return_dispatch')
        self.label('return_dispatch')
        # Static binary return tree; no indirect branch extension or host help.
        def dispatch(lo,hi):
            if hi-lo==1: self.jump(self.calls[lo]); return
            mid=(lo+hi)//2; self.li(11,mid); self.op(Op.LT,10,15,11); upper=self.new(); self.jump(upper,10); dispatch(lo,mid); self.label(upper); dispatch(mid,hi)
        dispatch(0,len(self.calls))


def compile_program(seq_len=4, config=CONFIG):
    """Compile a shape/length only; invariant across seeds and token values."""
    if isinstance(config,dict):
        values=config.get('configuration',config); config=TeachingConfig(**values)
    if type(seq_len) is not int or not 1<=seq_len<=config.max_seq: raise ValueError('Invalid sequence length')
    if config.n_layers%len(config.layer_pattern) or set(config.layer_pattern)-set('LF'): raise ValueError('Invalid layer pattern')
    if config.n_shared!=1 or not 1<=config.top_k<=config.n_experts: raise ValueError('Unsupported expert geometry')
    if any(k%2 for k in (config.d_model,config.mla_dc,config.kda_dim,config.kda_heads*config.kda_dim,config.n_heads*config.mla_dv,config.d_ff)): raise ValueError('Int4 fan-in must be even')
    return Builder(config,seq_len).build()
