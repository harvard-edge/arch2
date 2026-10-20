"""Shape-only canonical descriptor order (mirrors upstream tensor_list)."""
def tensor_layout(c):
    mats, entries = {}, []
    def param(n, size): entries.append((n, size * 2, None))
    def triple(n, k, out):
        mats[n] = k, out
        g = min(c.group_size, k)
        entries.extend([(n+'.q', k//2*out, None), (n+'.s', ((k+g-1)//g)*out*2, None), (n+'.z', ((k+g-1)//g)*out, None)])
    ng = (c.d_model+min(c.group_size,c.d_model)-1)//min(c.group_size,c.d_model)
    entries += [('emb.q',c.vocab*c.d_model//2,None),('emb.s',c.vocab*ng*2,None),('emb.z',c.vocab*ng,None)]
    types = (c.layer_pattern * (c.n_layers//len(c.layer_pattern)))
    for i,t in enumerate(types):
        p=f'L{i}.'
        for nm in ['res_attn.norm.w','res_attn.proj','norm1.w']: param(p+nm,c.d_model)
        if t=='F':
            for nm,k,n in [('wc',c.d_model,c.mla_dc),('wq_c',c.d_model,c.n_heads*c.mla_dk),('wq_r',c.d_model,c.n_heads*c.mla_dr),('wk_c',c.mla_dc,c.n_heads*c.mla_dk),('wk_r',c.d_model,c.mla_dr),('wv',c.mla_dc,c.n_heads*c.mla_dv),('o',c.n_heads*c.mla_dv,c.d_model)]: triple(p+'mla.'+nm,k,n)
            param(p+'mla.knorm.w',c.mla_dc)
        else:
            kd=c.kda_heads*c.kda_dim
            for nm,k,n in [('q',c.d_model,kd),('k',c.d_model,kd),('v',c.d_model,kd),('b',c.d_model,c.kda_heads),('f1',c.d_model,c.kda_dim),('f2',c.kda_dim,kd),('g1',c.d_model,c.kda_dim),('g2',c.kda_dim,kd),('o',kd,c.d_model)]: triple(p+'kda.'+nm,k,n)
            for nm,n in [('qconv',kd*c.conv_kernel),('kconv',kd*c.conv_kernel),('vconv',kd*c.conv_kernel),('A',c.kda_heads),('dtb',kd),('onorm.w',c.kda_dim)]: param(p+'kda.'+nm,n)
        for nm in ['res_mlp.norm.w','res_mlp.proj','norm2.w']: param(p+nm,c.d_model)
        triple(p+'moe.router',c.d_model,c.n_experts); param(p+'moe.bias',c.n_experts)
        for expert in ['shared']+[f'e{j}' for j in range(c.n_experts)]:
            for nm,k,n in [('g',c.d_model,c.d_ff),('u',c.d_model,c.d_ff),('d',c.d_ff,c.d_model)]: triple(p+'moe.'+expert+'.'+nm,k,n)
    for nm in ['res_out.norm.w','res_out.proj','final_norm.w']: param(nm,c.d_model)
    triple('head',c.d_model,c.vocab)
    return entries,mats
