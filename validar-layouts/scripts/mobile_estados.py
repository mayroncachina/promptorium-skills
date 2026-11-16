# mobile_estados.py: usado por captura.py no modo mobile. Uma tela de app muda quando se toca nela, então este
# script percorre os ESTADOS e mede cada um: (1) estado padrão, (2) cada controle tocável (botão, chip, aba,
# interruptor, abridor de folha), cada um depois de recarregar a tela, (3) cada carrossel rolado até o fim,
# (4) o fim da rolagem principal. Em cada estado procura: elemento coberto por outro (botão flutuante sobre a barra
# de navegação, último item atrás da barra fixa), transbordo lateral e controle que não muda nada ao ser tocado.
# Devolve um resumo para o checagens.json e grava estado-*.png em <out>/estados/.
import pathlib

MARCA = r"""() => {
 const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !e.disabled; };
 const nome = e => (e.getAttribute('aria-label') || e.innerText || e.title || e.tagName).trim().replace(/\s+/g, ' ').slice(0, 28);
 let i = 0; const lista = [];
 document.querySelectorAll('[data-vl-e]').forEach(e => e.removeAttribute('data-vl-e'));
 for (const e of document.querySelectorAll('button, [role=button], [role=radio], [role=checkbox], [role=switch], [role=tab]')) {
   if (!vis(e) || e.closest('nav')) continue;
   if (e.getAttribute('aria-checked') === 'true' || e.getAttribute('aria-pressed') === 'true' || e.getAttribute('aria-selected') === 'true' || e.getAttribute('aria-current') === 'true') continue;
   e.setAttribute('data-vl-e', i); lista.push({ i: i++, nome: nome(e) });
 }
 return lista.slice(0, 16);
}"""

ASSINA = "() => document.body.innerHTML.length + '|' + document.body.innerText.length + '|' + location.href"

CHECA = r"""() => {
 const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
 const nome = e => (e.getAttribute('aria-label') || e.innerText || e.tagName).trim().replace(/\s+/g, ' ').slice(0, 24);
 const cobertos = [];
 const els = [...document.querySelectorAll('a[href],button,input,select,textarea,[role=button],[role=radio],[role=checkbox],[role=switch]')].filter(vis);
 for (const e of els) {
   const r = e.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
   if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) continue;
   let recortado = false;   // fora da janela de uma área rolável: está só rolado para fora, não coberto
   for (let n = e.parentElement; n && n !== document.body; n = n.parentElement) {
     const s = getComputedStyle(n);
     if (/(auto|scroll|hidden|clip)/.test(s.overflowY + s.overflowX)) { const b = n.getBoundingClientRect(); if (cx < b.left || cx > b.right || cy < b.top || cy > b.bottom) { recortado = true; break; } }
   }
   if (recortado) continue;
   const t = document.elementFromPoint(cx, cy);
   if (!t || t === e || e.contains(t) || t.contains(e)) continue;
   let cortina = !!t.closest('[role=dialog],[aria-modal]');   // folha ou diálogo aberto cobre de propósito
   for (let n = t; n && n !== document.body && !cortina; n = n.parentElement) {
     const s = getComputedStyle(n), b = n.getBoundingClientRect();
     if (/(absolute|fixed)/.test(s.position) && b.width >= innerWidth * 0.9 && b.height >= innerHeight * 0.9) cortina = true;
   }
   if (cortina) continue;
   cobertos.push(nome(e) + ' coberto por ' + t.tagName.toLowerCase() + (t.getAttribute('aria-label') ? '[' + t.getAttribute('aria-label') + ']' : '') + (t.innerText ? ' "' + t.innerText.trim().slice(0, 18) + '"' : ''));
 }
 return { cobertos, transbordo: document.documentElement.scrollWidth > innerWidth + 1 };
}"""

ROLAGEM = r"""() => {
 const cs = [...document.querySelectorAll('*')].filter(e => { const s = getComputedStyle(e); return e.scrollWidth > e.clientWidth + 2 && /(auto|scroll)/.test(s.overflowX) && s.scrollSnapType !== 'none' && e.clientWidth > 0; });
 cs.forEach(e => e.setAttribute('data-vl-c', '1')); return cs.length;
}"""

def _abre(ctx, src, tw_css):
    pg = ctx.new_page(); pg.set_viewport_size({"width": 390, "height": 844})
    try: pg.goto(src.as_uri(), wait_until="networkidle", timeout=45000)
    except Exception: pg.goto(src.as_uri(), wait_until="load", timeout=45000)
    if tw_css: pg.add_style_tag(content=tw_css)
    pg.evaluate("() => document.fonts.ready"); pg.wait_for_timeout(500)
    return pg

def varrer(ctx, src, out, tw_css):
    pasta = out / "estados"; pasta.mkdir(exist_ok=True)
    lista, cobertos_distintos, sem_efeito, transbordo = [], set(), [], 0
    def registra(pg, rotulo, arq, extra=None):
        nonlocal transbordo
        pg.screenshot(path=str(pasta / arq))
        r = pg.evaluate(CHECA); cobertos_distintos.update(r["cobertos"]); transbordo += 1 if r["transbordo"] else 0
        item = {"estado": rotulo, "imagem": "estados/" + arq, "cobertos": r["cobertos"][:6], "transbordo": r["transbordo"]}
        if extra: item.update(extra)
        lista.append(item)
    pg = _abre(ctx, src, tw_css)
    registra(pg, "padrão", "00-padrao.png")
    controles = pg.evaluate(MARCA)
    # fim da rolagem principal (maior área que rola na vertical)
    pg.evaluate("""() => { const c = [...document.querySelectorAll('*')].filter(e => e.scrollHeight > e.clientHeight + 4 && /(auto|scroll)/.test(getComputedStyle(e).overflowY)).sort((a, b) => b.clientHeight - a.clientHeight)[0]; if (c) c.scrollTop = c.scrollHeight; }""")
    pg.wait_for_timeout(250); registra(pg, "fim da rolagem", "01-fim-rolagem.png")
    n_car = pg.evaluate(ROLAGEM)
    for k in range(min(n_car, 3)):   # carrosséis: rola o k-ésimo até o fim
        pg.evaluate("(k) => { const e = document.querySelectorAll('[data-vl-c]')[k]; e.scrollLeft = e.scrollWidth; }", k)
        pg.wait_for_timeout(350); registra(pg, f"carrossel {k + 1} no fim", f"02-carrossel-{k + 1}.png")
    pg.close()
    for c in controles:   # cada controle, numa tela recarregada
        pg = _abre(ctx, src, tw_css); pg.evaluate(MARCA)
        antes = pg.evaluate(ASSINA)
        try: pg.click(f'[data-vl-e="{c["i"]}"]', timeout=2500)
        except Exception: pg.close(); continue
        pg.wait_for_timeout(450)
        mudou = pg.evaluate(ASSINA) != antes
        if not mudou: sem_efeito.append(c["nome"])
        registra(pg, "toque em «" + c["nome"] + "»", f"10-toque-{c['i']:02d}.png", {"mudou": mudou})
        pg.close()
    return {"estados_testados": len(lista), "controles": len(controles), "carrosseis": n_car, "cobertos": len(cobertos_distintos), "cobertos_lista": sorted(cobertos_distintos)[:8],
            "transbordo": transbordo, "sem_efeito": sem_efeito, "lista": lista}
