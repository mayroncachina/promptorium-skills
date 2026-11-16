# componentes.py: usado por captura.py. Divide a tela em regiões (faixas da página) e
# componentes (cards, formulários, tabelas, gráficos, imagens, botões) e roda checagens por
# componente com o Playwright: contraste do texto, foco por teclado (Tab de verdade), alvo de
# toque, nome acessível, SVG sem aria-hidden, texto < 12px, transition-all e transbordo no
# celular. Cada elemento leva o número da linha do código-fonte (data-vl-l) para cruzar com o
# sloplint depois (temperatura.py).
import json, pathlib
from html.parser import HTMLParser

PESOS = {  # pontos de temperatura por tipo de problema (uma vez por tipo e componente)
    "contraste": 30, "contraste_grave": 10, "foco_invisivel": 35, "foco_fraco": 25, "foco_padrao": 12,
    "alvo_24": 25, "alvo_44": 8, "sem_nome": 30, "svg_sem_aria": 6, "texto_pequeno": 12,
    "transition_all": 6, "transborda": 35, "barra_5": 20, "gesto_so": 15, "campo_tipo": 8,
    "campo_fonte": 8, "alvo_junto": 8, "barra_altura": 10}
ROTULOS = {
    "contraste": "contraste abaixo de 4,5:1 (3:1 em texto grande)", "contraste_grave": "contraste abaixo de 3:1",
    "foco_invisivel": "foco de teclado invisível", "foco_fraco": "anel de foco com menos de 3:1",
    "foco_padrao": "só o foco padrão do navegador", "alvo_24": "alvo de toque menor que 24px",
    "alvo_44": "alvo de toque entre 24 e 43px", "sem_nome": "sem nome acessível (alt, label ou aria-label)",
    "svg_sem_aria": "SVG decorativo sem aria-hidden", "texto_pequeno": "texto menor que 12px",
    "transition_all": "transition: all", "transborda": "passa da largura da tela",
    "barra_5": "barra de navegação com mais de 5 itens", "gesto_so": "carrossel que só se troca por gesto (sem botão)",
    "campo_tipo": "campo sem inputmode/type adequado (teclado errado no celular)",
    "campo_fonte": "texto do campo menor que 16px (o iOS dá zoom ao focar)",
    "alvo_junto": "alvos de toque a menos de 8px um do outro",
    "barra_altura": "barra de navegação ou barra superior fora da altura usual (inferior 49-96px, superior 44px ou mais)"}

def instrumentar(path):
    """Cópia do HTML com data-vl-l="<linha>" em cada tag de abertura (_vl_linhas.html, ao lado)."""
    texto = path.read_text(errors="replace"); inicio = [0]
    for l in texto.split("\n")[:-1]: inicio.append(inicio[-1] + len(l) + 1)
    ins = []
    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            ln, col = self.getpos(); ins.append((inicio[ln - 1] + col + 1 + len(tag), ln))
        handle_startendtag = handle_starttag
    P(convert_charrefs=False).feed(texto)
    for pos, ln in sorted(ins, reverse=True):
        texto = texto[:pos] + f' data-vl-l="{ln}"' + texto[pos:]
    dst = path.with_name("_vl_linhas.html"); dst.write_text(texto); return dst

COMUM_JS = r"""
window.__vl = (() => {
 const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
   return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && parseFloat(s.opacity) > 0.05; };
 const rgba = c => { const m = (c || '').match(/rgba?\(([^)]+)\)/); if (!m) return null;
   const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
 const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
   return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
 const ratio = (a, b) => { const A = lum(a), B = lum(b); return (Math.max(A, B) + 0.05) / (Math.min(A, B) + 0.05); };
 const mix = (top, bot) => { const a = top[3]; return [0, 1, 2].map(i => top[i] * a + bot[i] * (1 - a)).concat([1]); };
 // fundo efetivo atrás do elemento; null quando há gradiente ou imagem no caminho
 const fundo = e => { const camadas = []; let n = e;
   while (n && n.nodeType === 1) { const s = getComputedStyle(n);
     if (s.backgroundImage && s.backgroundImage !== 'none') return null;
     const c = rgba(s.backgroundColor); if (c && c[3] > 0) { camadas.push(c); if (c[3] >= 1) break; }
     n = n.parentElement; }
   let base = [255, 255, 255, 1]; for (let i = camadas.length - 1; i >= 0; i--) base = mix(camadas[i], base); return base; };
 return { vis, rgba, ratio, mix, fundo };
})();
"""

FOCO_JS = r"""() => { const e = document.activeElement; if (!e || e === document.body || !e.dataset.vlId) return null;
 const s = getComputedStyle(e); const V = window.__vl;
 return { id: e.dataset.vlId, o: [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.borderColor, s.backgroundColor],
          fundo: V.fundo(e.parentElement || e) }; }"""

COMP_JS = r"""([vp, focoInfo]) => {
 const V = window.__vl, W = innerWidth, H = innerHeight;
 const box = e => { const r = e.getBoundingClientRect(); return { x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height) }; };
 const area = e => { const r = e.getBoundingClientRect(); return r.width * r.height; };
 const txt = e => (e.innerText || e.textContent || '').trim().replace(/\s+/g, ' ');
 const sig = e => !['SCRIPT', 'STYLE', 'LINK', 'META', 'TEMPLATE'].includes(e.tagName) && V.vis(e) && e.getBoundingClientRect().height >= 40;
 // display:contents (ex.: raiz do runtime do Claude Design) não tem caixa: conta pelos filhos
 const kids = e => [...e.children].flatMap(c => getComputedStyle(c).display === 'contents' ? kids(c) : [c]).filter(sig);
 const desce = e => { let t = e; while (kids(t).length === 1) t = kids(t)[0]; return t; };
 const naoDivide = ['NAV', 'HEADER', 'FOOTER', 'FORM', 'TABLE', 'ASIDE'];
 // 1. regiões: faixas de primeiro nível; faixas muito altas (> 1,5 tela) são divididas nos filhos
 let bandas = kids(desce(document.body));
 for (let g = 0; g < 4; g++) { const nb = []; let mudou = false;
   for (const b of bandas) { const t = desce(b), k = kids(t);
     const alto = b.getBoundingClientRect().height, tag = t.tagName;
     if (k.length >= 2 && !naoDivide.includes(b.tagName) && ((['MAIN', 'BODY'].includes(b.tagName) || ['MAIN'].includes(tag)) && alto > H || (b.tagName === 'DIV' && alto > 1.5 * H))) { nb.push(...k); mudou = true; } else nb.push(b); }
   bandas = nb; if (!mudou) break; }
 const titulo = e => { const h = e.querySelector('h1,h2,h3,h4'); return h ? txt(h).slice(0, 42) : ''; };
 const nomeRegiao = (e, i) => { const t = e.tagName, nav = e.querySelector('nav');
   if (t === 'NAV' || (nav && e.getBoundingClientRect().height < 160 && !e.querySelector('h1'))) return 'Navegação';
   if (t === 'FOOTER') return 'Rodapé'; if (t === 'ASIDE') return 'Barra lateral';
   if (t === 'FORM') return 'Formulário';
   const h1 = e.querySelector('h1'); if (h1) return (i <= 1 ? 'Hero · ' : 'Cabeçalho · ') + txt(h1).slice(0, 42);
   if (t === 'HEADER') return 'Cabeçalho' + (titulo(e) ? ' · ' + titulo(e) : '');
   return titulo(e) ? 'Seção · ' + titulo(e) : 'Bloco · ' + (txt(e).slice(0, 34) || (i + 1)); };
 const regioes = bandas.map((e, i) => ({ el: e, nome: nomeRegiao(e, i), tipo: 'região' }));
 // 2. componentes dentro das regiões
 const comps = [], usados = [];
 const dentro = e => usados.some(u => u !== e && u.contains(e));
 const add = (e, tipo, nome) => { if (dentro(e) || usados.includes(e)) return; usados.push(e); comps.push({ el: e, tipo, nome }); };
 const superficie = e => { const s = getComputedStyle(e), p = e.parentElement ? getComputedStyle(e.parentElement) : null;
   const bg = V.rgba(s.backgroundColor); return (bg && bg[3] > 0.04 && (!p || s.backgroundColor !== p.backgroundColor)) ||
     parseFloat(s.borderTopWidth) > 0 || parseFloat(s.borderLeftWidth) > 0 || s.boxShadow !== 'none' || s.backgroundImage !== 'none'; };
 for (const R of regioes) {
   const pais = [R.el, ...R.el.querySelectorAll('*')].filter(V.vis);
   for (const p of pais) { const grupos = {};
     for (const c of p.children) { if (!V.vis(c) || (c.matches('button,input,select,textarea,[role=button]') || (c.tagName === 'A' && !c.querySelector('h1,h2,h3,h4,h5'))) || area(c) < 6000 || c.getBoundingClientRect().height < 56 || !superficie(c)) continue;
       (grupos[c.tagName] = grupos[c.tagName] || []).push(c); }
     for (const g of Object.values(grupos)) {
       if (g.length < 2) continue;
       g.forEach(c => { const rot = titulo(c) || ((c.innerText || '').split('\n').map(l => l.trim()).find(l => /[A-Za-zÀ-ú]{3,}/.test(l)) || '').slice(0, 32);
         add(c, 'card', rot ? 'Card · ' + rot : 'Card (sem texto)'); }); } }
   R.el.querySelectorAll('form').forEach(f => add(f, 'formulário', 'Formulário' + (titulo(f) ? ' · ' + titulo(f) : '')));
   R.el.querySelectorAll('table').forEach(t => add(t, 'tabela', 'Tabela' + (titulo(t.closest('section,div') || t) ? ' · ' + titulo(t.closest('section,div')) : '')));
   R.el.querySelectorAll('canvas, svg, img, video').forEach(m => { if (V.vis(m) && area(m) >= 20000)
     add(m, m.tagName === 'IMG' || m.tagName === 'VIDEO' ? 'imagem' : 'gráfico', (m.tagName === 'IMG' ? 'Imagem' : m.tagName === 'VIDEO' ? 'Vídeo' : 'Gráfico/ilustração') + (m.getAttribute('alt') ? ' · ' + m.getAttribute('alt').slice(0, 30) : '')); });
   R.el.querySelectorAll('button, [role=button], input[type=submit], input[type=button], a[href]').forEach(b => {
     if (!V.vis(b)) return; const s = getComputedStyle(b), bg = V.rgba(s.backgroundColor);
     const estilizado = b.tagName !== 'A' || (bg && bg[3] > 0.04) || parseFloat(s.borderTopWidth) > 0;
     if (estilizado && parseFloat(s.paddingLeft) >= 8 && b.getBoundingClientRect().height >= 28)
       add(b, 'botão', 'Botão · ' + (txt(b) || b.getAttribute('aria-label') || b.value || 'sem texto').slice(0, 30)); });
 }
 // 3. checagens por elemento
 const prob = [];
 const P = (el, tipo, det) => prob.push({ el, tipo, det });
 const todos = [...document.body.querySelectorAll('*')].filter(V.vis);
 for (const e of todos) {
   const s = getComputedStyle(e);
   const temTexto = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
   if (temTexto) {
     const fs = parseFloat(s.fontSize), grande = fs >= 24 || (fs >= 18.66 && parseInt(s.fontWeight) >= 700);
     if (fs < 12) P(e, 'texto_pequeno', fs.toFixed(0) + 'px em "' + txt(e).slice(0, 30) + '"');
     const fg = V.rgba(s.color), bg = V.fundo(e);
     if (fg && bg && !s.webkitTextFillColor?.includes('rgba(0, 0, 0, 0)') && s.backgroundClip !== 'text') {
       let op = 1; for (let n = e; n && n.nodeType === 1; n = n.parentElement) op *= parseFloat(getComputedStyle(n).opacity);
       const cor = V.mix([fg[0], fg[1], fg[2], fg[3] * op], bg), r = V.ratio(cor, bg), lim = grande ? 3 : 4.5;
       if (r < lim) { P(e, 'contraste', r.toFixed(2).replace('.', ',') + ':1 em "' + txt(e).slice(0, 30) + '"'); if (r < 3) P(e, 'contraste_grave', r.toFixed(2).replace('.', ',') + ':1'); } } }
   if (s.transitionProperty.split(',').some(p => p.trim() === 'all') && s.transitionDuration.split(',').some(d => parseFloat(d) > 0)) P(e, 'transition_all', e.tagName.toLowerCase());
   if (e.tagName === 'svg' && e.getAttribute('aria-hidden') !== 'true' && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby') && !e.parentElement.closest('svg')) P(e, 'svg_sem_aria', 'svg');
   if (e.tagName === 'IMG' && !e.hasAttribute('alt')) P(e, 'sem_nome', 'imagem sem alt');
   if (['BUTTON', 'A'].includes(e.tagName) && !txt(e) && !e.getAttribute('aria-label') && !e.getAttribute('title') && !e.querySelector('img[alt]:not([alt=""])')) P(e, 'sem_nome', 'botão/link só com ícone');
   if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.tagName) && !['hidden', 'submit', 'button'].includes(e.type) && !(e.labels && e.labels.length) && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby')) P(e, 'sem_nome', 'campo sem rótulo');
   if (vp === 'mobile') {
     if (e.tagName === 'NAV') { const n = [...e.querySelectorAll('a[href],button')].filter(V.vis).length; if (n > 5) P(e, 'barra_5', n + ' itens');
       const rn = e.getBoundingClientRect(); if (rn.bottom > H - 4 && rn.top > H / 2 && (rn.height < 49 || rn.height > 96)) P(e, 'barra_altura', 'barra inferior de ' + Math.round(rn.height) + 'px'); }
     if (e.tagName === 'HEADER') { const rh = e.getBoundingClientRect(); if (rh.top < 44 && rh.height < 44) P(e, 'barra_altura', 'barra superior de ' + Math.round(rh.height) + 'px'); }
     if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.tagName) && !['hidden', 'checkbox', 'radio', 'submit', 'button'].includes(e.type) && parseFloat(s.fontSize) < 16) P(e, 'campo_fonte', parseFloat(s.fontSize) + 'px');
     if (/(auto|scroll)/.test(s.overflowX) && e.scrollWidth > e.clientWidth + 2 && s.scrollSnapType !== 'none') {
       const ctl = [...(e.parentElement || document.body).querySelectorAll('button,a[href]')].filter(b => !e.contains(b) && V.vis(b));
       if (ctl.length < 2) P(e, 'gesto_so', 'carrossel sem botões'); }
     if (e.tagName === 'INPUT' && (e.type || 'text') === 'text') {
       const lab = (e.labels && e.labels[0] ? e.labels[0].innerText : '') + ' ' + (e.placeholder || '') + ' ' + (e.getAttribute('aria-label') || '');
       if (/e-?mail|telefone|celular|cpf|cep|ddd|cart[ãa]o|valor|cvv/i.test(lab) && !e.getAttribute('inputmode')) P(e, 'campo_tipo', lab.trim().slice(0, 30)); }
     if (e.matches('a[href],button,input,select,textarea,[role=button]')) {
       const r = e.getBoundingClientRect(), inline = e.tagName === 'A' && e.parentElement && ['P', 'LI', 'SPAN'].includes(e.parentElement.tagName) && txt(e.parentElement).length > txt(e).length + 20;
       if (!inline && (r.width < 24 || r.height < 24)) P(e, 'alvo_24', Math.round(r.width) + '×' + Math.round(r.height) + 'px "' + (txt(e) || e.getAttribute('aria-label') || '').slice(0, 24) + '"');
       else if (!inline && (r.width < 44 || r.height < 44)) P(e, 'alvo_44', Math.round(r.width) + '×' + Math.round(r.height) + 'px'); }
     const r = e.getBoundingClientRect();
     if (r.right > W + 1 && r.width > 0 && !e.parentElement.closest('[style*="overflow"], .overflow-x-auto, .overflow-auto, .overflow-x-scroll')) {
       let rolavel = false; for (let n = e.parentElement; n && n !== document.body; n = n.parentElement) { const o = getComputedStyle(n).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') { rolavel = true; break; } }
       if (!rolavel) P(e, 'transborda', Math.round(r.right) + 'px numa tela de ' + W + 'px'); } }
   if (vp === 'desktop' && e.dataset.vlId && focoInfo[e.dataset.vlId]) { const f = focoInfo[e.dataset.vlId];
     if (f.status === 'invisivel') P(e, 'foco_invisivel', '"' + (txt(e) || e.getAttribute('aria-label') || e.tagName).slice(0, 24) + '"');
     else if (f.status === 'fraco') P(e, 'foco_fraco', f.det + ' em "' + (txt(e) || e.tagName).slice(0, 24) + '"');
     else if (f.status === 'padrao') P(e, 'foco_padrao', '"' + (txt(e) || e.tagName).slice(0, 24) + '"'); }
 }
 // 3b. espaçamento entre alvos de toque (mobile): menos de 8px entre dois alvos pequenos
 if (vp === 'mobile') {
   const al = [...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,[role=button],[role=radio],[role=checkbox],[role=switch]')].filter(V.vis);
   const ja = new Set();
   for (let i = 0; i < al.length; i++) for (let j = i + 1; j < al.length; j++) {
     const a = al[i], b = al[j]; if (ja.has(a) || a.contains(b) || b.contains(a)) continue;
     const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
     if (Math.min(ra.width, ra.height) >= 48 && Math.min(rb.width, rb.height) >= 48) continue;   // alvos grandes encostados (barra, segmentado) não confundem o toque
     const dx = Math.max(ra.left - rb.right, rb.left - ra.right), dy = Math.max(ra.top - rb.bottom, rb.top - ra.bottom);
     if ((dx >= 0 && dy < 0 && dx < 8) || (dy >= 0 && dx < 0 && dy < 8) || (dx < 0 && dy < 0)) { ja.add(a); P(a, 'alvo_junto', Math.max(0, Math.round(Math.max(dx, dy))) + 'px entre "' + (txt(a) || a.getAttribute('aria-label') || a.tagName).slice(0, 16) + '" e "' + (txt(b) || b.getAttribute('aria-label') || b.tagName).slice(0, 16) + '"'); }
   }
 }
 // 4. atribuição: componente mais interno que contém o elemento; senão a região
 const porArea = [...comps].sort((a, b) => area(a.el) - area(b.el));
 const linhas = el => { const ls = [el, ...el.querySelectorAll('[data-vl-l]')].map(x => +x.dataset.vlL).filter(Boolean); return ls.length ? [Math.min(...ls), Math.max(...ls)] : null; };
 const saida = (o, i, pre) => ({ id: pre + (i + 1), nome: o.nome, tipo: o.tipo, caixa: box(o.el), linhas: linhas(o.el), texto: txt(o.el).slice(0, 400), problemas: [] });
 const R = regioes.map((r, i) => saida(r, i, 'R')), C = comps.map((c, i) => saida(c, i, 'C'));
 C.forEach((c, i) => { const ri = regioes.findIndex(r => r.el.contains(comps[i].el)); c.regiao = ri >= 0 ? R[ri].id : null; });
 const pagina = { id: 'P', nome: 'Página (fora das regiões)', tipo: 'página', problemas: [] };
 for (const p of prob) {
   const ci = porArea.find(c => c.el.contains(p.el)); let alvo;
   if (ci) alvo = C[comps.indexOf(ci)]; else { const ri = regioes.findIndex(r => r.el.contains(p.el)); alvo = ri >= 0 ? R[ri] : pagina; }
   alvo.problemas.push({ tipo: p.tipo, det: p.det, linha: +(p.el.dataset.vlL || 0) || null });
 }
 return { viewport: { w: W, h: H, pagina: document.documentElement.scrollHeight, largura_doc: Math.max(W, document.documentElement.scrollWidth) }, regioes: R, componentes: C, pagina };
}"""

def _lum(c):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])

def _ratio(a, b):
    A, B = _lum(a), _lum(b); return (max(A, B) + 0.05) / (min(A, B) + 0.05)

def _cor(txt):
    import re
    m = re.search(r"rgba?\(([^)]+)\)", txt or "")
    if not m: return None
    p = [float(x) for x in re.split(r"[ ,/]+", m.group(1).strip()) if x]
    return p[:3] + [p[3] if len(p) > 3 else 1.0]

def foco_por_tab(pg):
    """Percorre a página com Tab (foco de teclado real) e classifica o indicador de foco de cada elemento."""
    n = pg.evaluate("""() => { let i = 0; document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"]),[role=button]')
        .forEach(e => e.setAttribute('data-vl-id', 'f' + (i++))); return i; }""")
    base = pg.evaluate("""() => Object.fromEntries([...document.querySelectorAll('[data-vl-id]')].map(e => { const s = getComputedStyle(e);
        return [e.dataset.vlId, [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.borderColor, s.backgroundColor]]; }))""")
    pg.evaluate("() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); }")
    info, vistos = {}, 0
    for _ in range(min(n, 150) + 2):
        pg.keyboard.press("Tab")
        r = pg.evaluate(FOCO_JS)
        if not r: continue
        if r["id"] in info: break
        vistos += 1
        o, b0, fundo = r["o"], base.get(r["id"]), r["fundo"]
        mudou = b0 is not None and o != b0
        if o[0] == "auto" and (b0 is None or o[3:] == b0[3:]):
            info[r["id"]] = {"status": "padrao"}; continue
        if not mudou or (o[0] == "none" and o[3] == (b0 or o)[3] and o[4:] == (b0 or o)[4:]):
            info[r["id"]] = {"status": "invisivel"}; continue
        oc = _cor(o[2])   # contorno transparente (ex.: outline-none do Tailwind) não conta: vale o anel em box-shadow
        if o[0] not in ("none", "auto") and float(o[1].replace("px", "") or 0) > 0 and oc and oc[3] > 0.1: cor = oc
        else:
            import re as _re
            cores = [_cor(c) for c in _re.findall(r"rgba?\([^)]+\)", o[3] or "")]
            cores = [c for c in cores if c and c[3] > 0.1]
            cor = cores[-1] if cores else None
        if cor and fundo:
            rr = _ratio(cor[:3], fundo[:3])
            info[r["id"]] = {"status": "fraco" if rr < 3 else "ok", "det": f"{rr:.2f}:1".replace(".", ",")}
        else:
            info[r["id"]] = {"status": "ok"}
    return info

def passe(ctx, src, out, tw_css, viewports=(("desktop", 1440, 900), ("mobile", 390, 844))):
    """Abre a cópia instrumentada em cada largura, mede os componentes e salva componentes-<vp>.json + tela inteira."""
    linhas = instrumentar(src)
    for nome, w, h in viewports:
        pg = ctx.new_page(); pg.set_viewport_size({"width": w, "height": h})
        try: pg.goto(linhas.as_uri(), wait_until="networkidle", timeout=45000)
        except Exception: pg.goto(linhas.as_uri(), wait_until="load", timeout=45000)
        if tw_css: pg.add_style_tag(content=tw_css)
        pg.evaluate("() => document.fonts.ready"); pg.wait_for_timeout(600)
        pg.evaluate(COMUM_JS)
        foco = foco_por_tab(pg) if nome == "desktop" else {}
        pg.evaluate("() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); }")
        pg.wait_for_timeout(200)
        dados = pg.evaluate(COMP_JS, [nome, foco])
        dados["foco_resumo"] = {s: sum(1 for v in foco.values() if v["status"] == s) for s in ("ok", "padrao", "fraco", "invisivel")}
        pg.screenshot(path=str(out / f"comp-{nome}.png"), full_page=True)
        (out / f"componentes-{nome}.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1))
        pg.close()
