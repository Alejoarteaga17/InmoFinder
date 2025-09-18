(function(){
    const $ = id => document.getElementById(id);
    const clamp0 = v => Math.max(0, Number(v||0));

    const pmr = $('precio_min_range'), pm = $('precio_min');
    const pxr = $('precio_max_range'), px = $('precio_max');

    const MIN = 0, MAX = 1_000_000_000, STEP = 50_000;

    [pm, px].forEach(inp => { if (inp){ inp.min=MIN; inp.max=MAX; inp.step=STEP; } });
    [pmr, pxr].forEach(r => { if (r){ r.min=MIN; r.max=MAX; r.step=STEP; } });

    const syncRange = (range, number) => {
        if(!range || !number) return;
        range.addEventListener('input', e=>{
            number.value = e.target.value;
        });
        number.addEventListener('input', e=>{
            range.value = clamp0(e.target.value);
        });
    };

    syncRange(pmr, pm);
    syncRange(pxr, px);
})();