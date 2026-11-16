# inventario.py: usado por captura.py. Lista os widgets da tela (botões de ação, ícones, campos, cartões,
# seletores, interruptores, cabeçalho, barra de navegação) com tamanho, forma e tipo, para o
# consistencia.py comparar entre telas. Salva inventario.json e recortes dos botões em widgets/.
import json, pathlib
from componentes import COMUM_JS, instrumentar

INV_JS = r"""
() => {
 const { vis, rgba, ratio, mix, fundo } = window.__vl;
 const norm = t => (t || '').replace(/\s+/g, ' ').trim();
 const px = v => Math.round(parseFloat(v) || 0);
 const raio = (s, r) => { const v = Math.max(px(s.borderTopLeftRadius), px(s.borderTopRightRadius));
   return v >= Math.min(r.width, r.height) / 2 - 0.5 ? 999 : v; };
 const lados = s => ['Top', 'Right', 'Bottom', 'Left'].map(l => parseFloat(s['border' + l + 'Width']) > 0 &&
   s['border' + l + 'Style'] !== 'none' && (rgba(s['border' + l + 'Color']) || [0, 0, 0, 1])[3] > 0 ? 1 : 0);
 const sombra = s => (s.boxShadow && s.boxShadow !== 'none' ? 1 : 0);
 const base = (kind, e, r, s) => { const d = e.closest('[data-vl-variante]'), l = e.closest('[data-vl-l]');
   return { kind, linha: l ? +l.dataset.vlL : 0, x: Math.round(r.left), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height),
     raio: raio(s, r), declarado: d ? d.dataset.vlVariante || 'sim' : null }; };
 const pai = e => (e.parentElement && fundo(e.parentElement)) || [255, 255, 255, 1];
 // segmento de controle segmentado: dentro de um pai com cantos arredondados que recorta o conteúdo
 const segmento = e => { const pe = e.parentElement; if (!pe) return false; const ps = getComputedStyle(pe);
   return ps.overflow === 'hidden' && parseFloat(ps.borderTopLeftRadius) > 0 && pe.children.length >= 2 && px(getComputedStyle(e).borderTopLeftRadius) === 0; };
 const itens = [], usados = new Set(), W = innerWidth, H = innerHeight;

 for (const e of document.querySelectorAll('button,a,[role=button],input[type=button],input[type=submit],summary')) {
   if (!vis(e) || e.closest('nav,[role=navigation],[role=tablist],[role=menubar]')) continue;
   const r = e.getBoundingClientRect(), s = getComputedStyle(e), rot = norm(e.innerText || e.value || '');
   const nome = rot || e.getAttribute('aria-label') || '';
   usados.add(e);
   if (e.matches('[role=switch]')) { itens.push({ ...base('interruptor', e, r, s), rotulo: nome }); continue; }
   if (e.matches('[aria-pressed],[aria-selected],[role=tab],[role=radio],[role=checkbox],[role=menuitemradio]')) {
     itens.push({ ...base('seletor', e, r, s), rotulo: nome, fonte: px(s.fontSize), peso: +s.fontWeight, larg: segmento(e) ? 'segmento' : r.width >= 0.6 * W ? 'em linha' : 'compacto' }); continue; }
   const bg = rgba(s.backgroundColor), b = lados(s), temBg = (bg && bg[3] > 0.05) || (s.backgroundImage && s.backgroundImage !== 'none');
   if (e.tagName === 'A' && !e.matches('[role=button]') && !temBg && !b.some(Boolean)) continue;   // link comum
   if (r.height > 72 && r.width >= 100) { itens.push({ ...base('atalho', e, r, s), rotulo: nome, borda: b.reduce((a, c) => a + c, 0), sombra: sombra(s) }); continue; }
   if (rot && r.width <= 64 && Math.abs(r.width - r.height) <= 6 && /^\d{1,2}(\s.*)?$/.test(rot)) {   // número ou texto curto num quadrado (dia do calendário, valor): é seletor
     itens.push({ ...base('seletor', e, r, s), rotulo: nome, fonte: px(s.fontSize), peso: +s.fontWeight, larg: 'quadrado' }); continue; }
   if (!rot || (r.width <= 64 && Math.abs(r.width - r.height) <= 6)) { const ic = base('icone', e, r, s);
     ic.aparencia = !temBg && !b.some(Boolean) ? 'sem fundo' : ic.raio === 999 ? 'redondo' : 'com fundo'; itens.push({ ...ic, rotulo: nome }); continue; }
   const fp = pai(e); let variante;
   if (s.backgroundImage && s.backgroundImage !== 'none') variante = 'cheio';
   else if (bg && bg[3] > 0.5) variante = ratio(mix(bg, fp), fp) >= 2.2 ? 'cheio' : 'tonal';
   else variante = b.some(Boolean) ? 'contorno' : 'texto';
   // largura útil do bloco (sem o padding); botões lado a lado contam juntos
   const pe = e.parentElement, ps = pe ? getComputedStyle(pe) : null;
   const pw = pe ? pe.getBoundingClientRect().width - parseFloat(ps.paddingLeft) - parseFloat(ps.paddingRight) : W;
   const fila = pe && ps.display.includes('flex') && ps.flexDirection === 'row' ? [...pe.children].reduce((a, c) => a + c.getBoundingClientRect().width, 0) : r.width;
   itens.push({ ...base('acao', e, r, s), rotulo: rot.slice(0, 40), variante, fonte: px(s.fontSize), peso: +s.fontWeight,
     larg: Math.max(r.width, fila) >= 0.9 * pw ? 'cheia' : 'ajustada' });
 }

 for (const e of document.querySelectorAll('input:not([type=checkbox]):not([type=radio]):not([type=hidden]):not([type=range]):not([type=button]):not([type=submit]),select,textarea')) {
   if (!vis(e)) continue;
   let caixa = e, s = getComputedStyle(e);
   if (!lados(s).some(Boolean) && e.parentElement && lados(getComputedStyle(e.parentElement)).some(Boolean)) { caixa = e.parentElement; }
   const cs = getComputedStyle(caixa), r = caixa.getBoundingClientRect(), b = lados(cs);
   const estilo = b.every(Boolean) ? 'contorno' : b[2] && !b[0] ? 'sublinhado' : 'preenchido';
   itens.push({ ...base('campo', caixa, r, cs), rotulo: e.getAttribute('aria-label') || e.placeholder || e.name || e.type, estilo, fonte: px(s.fontSize) });
 }


 const cand = [];
 for (const e of document.querySelectorAll('div,section,article,li,a,label')) {
   if (usados.has(e) || !vis(e) || e.closest('nav,[role=navigation],header')) continue;
   const r = e.getBoundingClientRect(), s = getComputedStyle(e);
   if (r.width < 120 || r.height < 56 || r.height > 420 || r.width > W - 4) continue;
   const rd = raio(s, r), bg = rgba(s.backgroundColor), b = lados(s);
   const fp = pai(e); const difere = bg && bg[3] > 0.5 && ratio(mix(bg, fp), fp) > 1.03;
   if (rd >= 6 && (sombra(s) || b.some(Boolean) || difere) && e.children.length >= 1) cand.push(e);
 }
 const cs = new Set(cand);
 for (const e of cand) { let p = e.parentElement, dentro = false; while (p) { if (cs.has(p)) { dentro = true; break; } p = p.parentElement; }
   if (dentro) continue; const r = e.getBoundingClientRect(), s = getComputedStyle(e);
   itens.push({ ...base('cartao', e, r, s), rotulo: norm(e.innerText).slice(0, 30), borda: lados(s).reduce((a, c) => a + c, 0), sombra: sombra(s) }); }

 const topo = [...document.querySelectorAll('header,[role=banner],body *')].find(e => { if (!vis(e)) return false;
   const r = e.getBoundingClientRect(), s = getComputedStyle(e);
   return r.top <= 2 && r.width >= 0.9 * W && r.height <= 120 && (e.matches('header,[role=banner]') || s.position === 'fixed' || s.position === 'sticky'); });
 if (topo) { const r = topo.getBoundingClientRect(), s = getComputedStyle(topo);
   itens.push({ ...base('cabecalho', topo, r, s), rotulo: norm(topo.innerText).slice(0, 30), borda: lados(s)[2], sombra: sombra(s) }); }
 for (const e of document.querySelectorAll('nav,[role=tablist],[role=navigation]')) { if (!vis(e)) continue;
   const r = e.getBoundingClientRect(), s = getComputedStyle(e);
   if (r.bottom < H * 0.75 && s.position !== 'fixed') continue;
   itens.push({ ...base('navegacao', e, r, s), rotulo: 'barra inferior', filhos: e.querySelectorAll('a,button,[role=tab]').length }); }
 return itens;
}
"""

def varrer(ctx, src, out, tw_css, vp=("mobile", 390, 844)):
    nome, w, h = vp
    linhas = src.with_name("_vl_linhas.html")
    if not linhas.exists(): linhas = instrumentar(src)
    pg = ctx.new_page(); pg.set_viewport_size({"width": w, "height": h})
    try: pg.goto(linhas.as_uri(), wait_until="networkidle", timeout=45000)
    except Exception: pg.goto(linhas.as_uri(), wait_until="load", timeout=45000)
    if tw_css: pg.add_style_tag(content=tw_css)
    pg.evaluate("() => document.fonts.ready"); pg.wait_for_timeout(600)
    pg.evaluate(COMUM_JS)
    itens = pg.evaluate(INV_JS)
    pasta = out / "widgets"; pasta.mkdir(exist_ok=True)
    for i, it in enumerate([x for x in itens if x["kind"] in ("acao", "icone")][:30]):   # recortes para o painel lado a lado
        try:
            pg.screenshot(path=str(pasta / f"{it['kind']}-{i:02d}.png"), full_page=True,
                          clip={"x": max(0, it["x"] - 4), "y": max(0, it["y"] - 4), "width": it["w"] + 8, "height": it["h"] + 8})
            it["img"] = f"widgets/{it['kind']}-{i:02d}.png"
        except Exception: pass
    pg.close()
    (out / "inventario.json").write_text(json.dumps({"vp": nome, "itens": itens}, ensure_ascii=False, indent=1))
    return {k: sum(1 for x in itens if x["kind"] == k) for k in sorted({x["kind"] for x in itens})}
