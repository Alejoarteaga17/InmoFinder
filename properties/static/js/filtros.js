(function(){
    const $ = id => document.getElementById(id);
    const clamp0 = v => {
        // Preserve empty input (used to deselect/clear filter)
        if (v === '' || v === null || v === undefined) return '';
        return Math.max(0, Number(v || 0));
    };

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
            const val = e.target.value;
            // If user clears the number input, do not force it back to 0
            // Leave the range as-is (visual), so the filter can be truly cleared
            if (val === '' || val === null || val === undefined) {
                // Optionally mark state for styling if needed
                number.dataset.empty = '1';
                return;
            }
            number.dataset.empty = '0';
            const num = Number(val);
            if (Number.isNaN(num)) {
                // Ignore intermediate invalid states (e.g., '-')
                return;
            }
            range.value = Math.max(0, num);
        });
    };

    syncRange(pmr, pm);
    syncRange(pxr, px);

    // Allow unchecking single-option radios (e.g., garage, pets)
    // Delegated listeners so it survives dynamic DOM updates
    const installDelegatedAllowUncheck = () => {
        if (window.__allowUncheckInstalled) return;
        window.__allowUncheckInstalled = true;

        const wasCheckedMap = new WeakMap();
        const captureTarget = (el) => {
            if (!el) return;
            wasCheckedMap.set(el, !!el.checked);
        };

        // Capture before default toggling happens (supports mouse/touch)
        document.addEventListener('pointerdown', (e) => {
            const r = e.target && e.target.closest && e.target.closest('input.allow-uncheck[type="radio"]');
            if (!r) return;
            captureTarget(r);
        }, true);

        // Keyboard accessibility (Space/Enter)
        document.addEventListener('keydown', (e) => {
            if (e.key !== ' ' && e.key !== 'Enter') return;
            const r = e.target && e.target.closest && e.target.closest('input.allow-uncheck[type="radio"]');
            if (!r) return;
            captureTarget(r);
        }, true);

        // Toggle off if it was checked before the interaction
        document.addEventListener('click', (e) => {
            const r = e.target && e.target.closest && e.target.closest('input.allow-uncheck[type="radio"]');
            if (!r) return;
            const was = wasCheckedMap.get(r);
            if (was) {
                e.preventDefault();
                r.checked = false;
                r.dispatchEvent(new Event('change', { bubbles: true }));
            }
            wasCheckedMap.set(r, false);
        }, true);
    };

    installDelegatedAllowUncheck();
})();