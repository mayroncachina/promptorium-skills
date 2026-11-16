# captura.py <arquivo.html> <pasta_saida> [--tools /tmp/vl-tools] [--modo mobile|desktop]
# Modo desktop: renderiza em 1440x900 e 390x844. Modo mobile: só o celular (390x844, mais 320, 360, 430 e paisagem),
# com varredura de estados (mobile_estados.py). Sem --modo, o modo vem do _vl_artboards.json (artboard até 500px = mobile).
# Salva screenshots e as
# checagens ui-ux-pro-max em checagens.json. O workspace bloqueia CDNs: o script
# intercepta Tailwind Play CDN, jsDelivr/unpkg (/npm/) e Google Fonts e serve o mesmo
# conteúdo a partir do registro npm. O que não der para servir vai para "bloqueados".
import sys, json, re, pathlib, subprocess, tarfile, urllib.parse, mimetypes
from playwright.sync_api import sync_playwright

args = sys.argv[1:]
TOOLS = pathlib.Path(args[args.index("--tools") + 1] if "--tools" in args else "/tmp/vl-tools")
src = pathlib.Path(args[0]).resolve(); out = pathlib.Path(args[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
MODO = args[args.index("--modo") + 1] if "--modo" in args else None
if not MODO:   # automático: lê o que o dc_montar.py gravou ao lado do artboard
    MODO = "desktop"
    try:
        for a in json.load(open(src.parent / "_vl_artboards.json")):
            if pathlib.Path(a["html"]).resolve() == src: MODO = a.get("modo", "desktop")
    except Exception: pass
CACHE = TOOLS / "npm-cache"; CACHE.mkdir(parents=True, exist_ok=True)
bloqueados, servidos, uso_tw = set(), set(), {"cdn": False, "plugins": []}

def npm_pkg(spec):
    """Baixa e extrai um pacote do registro npm; devolve a pasta 'package' ou None."""
    dest = CACHE / re.sub(r"[^A-Za-z0-9._-]", "_", spec)
    if not (dest / "package").exists():
        dest.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["npm", "pack", spec, "--silent", "--pack-destination", str(dest)],
                           capture_output=True, text=True, timeout=120)
        tgz = [l for l in r.stdout.split() if l.endswith(".tgz")]
        if r.returncode or not tgz: return None
        with tarfile.open(dest / tgz[-1]) as t: t.extractall(dest, filter="data")
    return dest / "package"

def npm_file(rest):
    m = re.match(r"^((?:@[^/]+/)?[^/@]+)(?:@([^/]+))?(/.*)?$", rest)
    if not m: return None
    name, ver, path = m.group(1), m.group(2) or "latest", (m.group(3) or "").lstrip("/")
    pkg = npm_pkg(f"{name}@{ver}")
    if not pkg: return None
    if not path:
        meta = json.loads((pkg / "package.json").read_text())
        br = meta.get("browser") if isinstance(meta.get("browser"), str) else None
        path = meta.get("jsdelivr") or meta.get("unpkg") or br or meta.get("main") or "index.js"
    f = pkg / path
    for cand in (f, f.with_suffix(f.suffix + ".js"), f / "index.js"):
        if cand.is_file(): return cand
    return None

def google_fonts_css(url, base="https://fonts.local/"):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    css = []
    for fam in q.get("family", []):
        for one in fam.split("|"):
            name = one.split(":")[0].replace("+", " ").strip()
            slug = re.sub(r"\s+", "-", name.lower())
            pkg = npm_pkg(f"@fontsource/{slug}")
            if not pkg: bloqueados.add(f"fonte: {name}"); continue
            servidos.add(f"fonte: {name} (@fontsource)")
            for f in sorted((pkg / "files").glob(f"{slug}-latin-*.woff2")):
                m = re.match(rf"{re.escape(slug)}-latin-(\d+)-(normal|italic)\.woff2$", f.name)
                if m:
                    css.append(f"@font-face{{font-family:'{name}';font-style:{m.group(2)};font-weight:{m.group(1)};"
                               f"font-display:swap;src:url({base}{slug}/{f.name}) format('woff2');}}")
    return "\n".join(css)

def rota(route):
    url = route.request.url; u = urllib.parse.urlparse(url)
    if u.scheme in ("file", "data", "blob") or u.hostname in ("localhost", "127.0.0.1"):
        return route.continue_()
    try:
        if u.hostname == "cdn.tailwindcss.com":
            uso_tw["cdn"] = True; servidos.add("Tailwind Play CDN (recompilado com tailwindcss@3)")
            pl = urllib.parse.parse_qs(u.query).get("plugins", [""])[0]
            uso_tw["plugins"] = [x.strip() for x in pl.split(",") if x.strip()]
            return route.fulfill(status=200, content_type="application/javascript",
                                 body="window.tailwind=window.tailwind||{config:{}};")
        if u.hostname in ("cdn.jsdelivr.net", "unpkg.com") and not u.path.startswith("/gh/"):
            rest = u.path[len("/npm/"):] if u.path.startswith("/npm/") else u.path.lstrip("/")
            f = npm_file(rest)
            if f:
                servidos.add(url)
                return route.fulfill(status=200, body=f.read_bytes(),
                                     content_type=mimetypes.guess_type(f.name)[0] or "application/javascript")
        if u.hostname == "fonts.googleapis.com":
            return route.fulfill(status=200, content_type="text/css", body=google_fonts_css(url))
        if u.hostname == "fonts.local":
            _, slug, fname = u.path.split("/", 2)
            return route.fulfill(status=200, content_type="font/woff2",
                                 body=(npm_pkg(f"@fontsource/{slug}") / "files" / fname).read_bytes())
    except Exception as e:
        bloqueados.add(f"{url} ({e.__class__.__name__})"); return route.abort()
    bloqueados.add(url); return route.abort()

def tailwind_css(page):
    cfg = page.evaluate("() => { try { return JSON.stringify((window.tailwind||{}).config||{}) } catch(e) { return '{}' } }")
    extra = page.evaluate("() => [...document.querySelectorAll('style[type=\"text/tailwindcss\"]')].map(s=>s.textContent).join('\\n')")
    (out / "_tw.html").write_text(page.content())
    # só os plugins que a página pediu no CDN (?plugins=...): o aspect-ratio, se carregado à toa,
    # desliga as classes nativas aspect-* do Tailwind 3
    plug = [TOOLS / "node_modules/@tailwindcss" / p for p in uso_tw["plugins"]]
    reqs = ", ".join(f"require({json.dumps(str(p))})" for p in plug if p.exists())
    (out / "_tw.config.js").write_text(
        f"module.exports = Object.assign({cfg}, {{content: [{json.dumps(str(out / '_tw.html'))}], plugins: [{reqs}]}});")
    (out / "_tw.in.css").write_text("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n" + extra)
    r = subprocess.run([str(TOOLS / "node_modules/.bin/tailwindcss"), "-c", str(out / "_tw.config.js"),
                        "-i", str(out / "_tw.in.css"), "-o", str(out / "_tw.css")],
                       capture_output=True, text=True, timeout=180)
    return (out / "_tw.css").read_text() if r.returncode == 0 else None


def snapshot(page):
    """HTML autossuficiente ao lado da cópia do layout (_vl_render.html): CSS do Tailwind já
    embutido, fontes e pacotes de CDN copiados para _vl_assets/, scripts removidos."""
    import html as H, shutil
    d = src.parent; assets = d / "_vl_assets"; assets.mkdir(exist_ok=True)
    s = page.content()
    s = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", s, flags=re.I)
    # canvas desenhado por JS guarda a largura do desktop em atributos/estilo: no snapshot ele volta a ser fluido
    s = re.sub(r"<canvas\b([^>]*)>", lambda m: "<canvas" + re.sub(r'\s(?:width|height|style)="[^"]*"', "", m.group(1))
               + ' style="display:block;width:100%;height:100%"' + ">", s, flags=re.I)
    def fonts(m):
        href = H.unescape(re.search(r'href="([^"]+)"', m.group(0)).group(1))
        css = google_fonts_css(href, base="_vl_assets/fonts/")
        for slug, fname in re.findall(r"_vl_assets/fonts/([^/]+)/([^)]+)\)", css):
            (assets / "fonts" / slug).mkdir(parents=True, exist_ok=True)
            shutil.copy(npm_pkg(f"@fontsource/{slug}") / "files" / fname, assets / "fonts" / slug / fname)
        return f"<style>{css}</style>"
    s = re.sub(r"<link[^>]+fonts\.googleapis\.com/css[^>]*>", fonts, s, flags=re.I)
    def vendor(m):
        u = urllib.parse.urlparse(H.unescape(m.group(2)))
        rest = u.path[len("/npm/"):] if u.path.startswith("/npm/") else u.path.lstrip("/")
        f = npm_file(rest)
        if not f: return m.group(0)
        pkg = next(p for p in f.parents if p.name == "package")
        dest = assets / re.sub(r"[^A-Za-z0-9._-]", "_", str(pkg.parent.name))
        if not dest.exists(): shutil.copytree(pkg, dest)
        return f'{m.group(1)}="{(dest / f.relative_to(pkg)).relative_to(d)}"'
    s = re.sub(r'(href|src)="(https://(?:cdn\.jsdelivr\.net|unpkg\.com)/[^"]+)"', vendor, s)
    (d / "_vl_render.html").write_text(s)
    return d / "_vl_render.html"

JS = r"""() => {
 const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none'; };
 const sel = e => e.tagName.toLowerCase() + (e.id?'#'+e.id:'') + (typeof e.className==='string' && e.className.trim() ? '.'+e.className.trim().split(/\s+/).slice(0,2).join('.') : '');
 const inter = [...document.querySelectorAll('a[href],button,input,select,textarea,[role=button],[onclick]')].filter(vis);
 const small = inter.filter(e => { const r = e.getBoundingClientRect(); return r.width<44 || r.height<44; });
 const tiny24 = inter.filter(e => { const r = e.getBoundingClientRect(); return r.width<24 || r.height<24; });
 const txt = [...document.querySelectorAll('body *')].filter(e => vis(e) && [...e.childNodes].some(n => n.nodeType===3 && n.textContent.trim()));
 const tiny = txt.filter(e => parseFloat(getComputedStyle(e).fontSize) < 12);
 const fields = [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]),select,textarea')];
 const unlabeled = fields.filter(f => !(f.labels && f.labels.length) && !f.getAttribute('aria-label') && !f.getAttribute('aria-labelledby'));
 const iconBtn = [...document.querySelectorAll('button,a[href]')].filter(b => vis(b) && !b.textContent.trim() && !b.getAttribute('aria-label') && !b.getAttribute('title'));
 const hs = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => +h.tagName[1]);
 let jumps = 0; for (let i=1;i<hs.length;i++) if (hs[i]-hs[i-1]>1) jumps++;
 const fams = new Set(txt.slice(0,400).map(e => getComputedStyle(e).fontFamily.split(',')[0].replace(/["']/g,'').trim()));
 const loaded = [...document.fonts].filter(f => f.status==='loaded').map(f => f.family.replace(/["']/g,''));
 return {
  viewport_meta: !!document.querySelector('meta[name=viewport]'), lang: document.documentElement.getAttribute('lang') || null,
  title: document.title || null, meta_description: !!document.querySelector('meta[name=description]'), favicon: !!document.querySelector('link[rel*=icon]'),
  overflow_x: document.documentElement.scrollWidth > window.innerWidth + 1, altura_pagina: document.documentElement.scrollHeight,
  img_sem_alt: [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).length,
  emoji_em_texto: (document.body.innerText.match(/(?![©®™])\p{Extended_Pictographic}/gu) || []).length,
  alvos_toque_pequenos: small.length, alvos_menor_24: tiny24.length, alvos_menor_48: inter.filter(e => { const r = e.getBoundingClientRect(); return r.width<48 || r.height<48; }).length, exemplos_alvos: small.slice(0,5).map(sel), exemplos_menor_24: tiny24.slice(0,5).map(sel),
  texto_menor_12px: tiny.length, exemplos_texto: tiny.slice(0,5).map(sel),
  campos_sem_label: unlabeled.length, botoes_icone_sem_nome: iconBtn.length,
  div_clicavel: document.querySelectorAll('div[onclick],span[onclick]').length,
  h1: hs.filter(h=>h===1).length, saltos_de_titulo: jumps,
  familias_em_uso: [...fams].slice(0,6), fontes_carregadas: [...new Set(loaded)].slice(0,8),
  tem_nav: !!document.querySelector('nav'), tem_main: !!document.querySelector('main'), tem_footer: !!document.querySelector('footer'),
  tem_form: fields.length > 0, interativos: inter.length, palavras: document.body.innerText.split(/\s+/).filter(Boolean).length
 };
}"""

res = {}
with sync_playwright() as p:
    try: b = p.chromium.launch()
    except Exception: b = p.chromium.launch(channel="chrome")   # sem o Chromium do Playwright: usa o Chrome do sistema
    ctx = b.new_context(); ctx.route("**/*", rota)
    tw_css = None
    VPS = {"mobile": (390, 844)} if MODO == "mobile" else {"desktop": (1440, 900), "mobile": (390, 844)}
    for nome, (w, h) in VPS.items():
        pg = ctx.new_page(); pg.set_viewport_size({"width": w, "height": h})
        erros = []
        pg.on("console", lambda m, e=erros: m.type == "error" and e.append(m.text))
        pg.on("pageerror", lambda x, e=erros: e.append(str(x)))
        try: pg.goto(src.as_uri(), wait_until="networkidle", timeout=45000)
        except Exception: pg.goto(src.as_uri(), wait_until="load", timeout=45000)
        if uso_tw["cdn"]:
            tw_css = tw_css or tailwind_css(pg)
            if tw_css: pg.add_style_tag(content=tw_css)
            else: bloqueados.add("Tailwind: falha ao recompilar")
        pg.evaluate("() => document.fonts.ready"); pg.wait_for_timeout(800)
        pg.screenshot(path=str(out / f"{nome}-dobra.png"))
        pg.screenshot(path=str(out / f"{nome}-inteira.png"), full_page=True)
        if nome == next(iter(VPS)): res["snapshot"] = str(snapshot(pg))
        res[nome] = pg.evaluate(JS)
        res[nome]["erros_console"] = [e for e in erros if "ERR_FAILED" not in e][:10]
        pg.close()
    # Conjunto de telas que o review-finish do Hallmark espera, já com CSS e fontes (shots/)
    (out / "shots").mkdir(exist_ok=True)
    SHOTS = ((375, 812, True, "index-375"), (390, 844, False, "index-390"), (360, 800, False, "index-360"),
             (430, 932, False, "index-430")) if MODO == "mobile" else (
            (1280, 800, False, "index-1280x800"), (1440, 900, False, "index-1440x900"),
            (1920, 1080, False, "index-1920x1080"), (1440, 900, True, "index-1440-full"), (375, 812, True, "index-375"))
    for (w, h, full, nome) in SHOTS:
        pg = ctx.new_page(); pg.set_viewport_size({"width": w, "height": h})
        try: pg.goto(src.as_uri(), wait_until="networkidle", timeout=45000)
        except Exception: pg.goto(src.as_uri(), wait_until="load", timeout=45000)
        if tw_css: pg.add_style_tag(content=tw_css)
        pg.evaluate("() => document.fonts.ready"); pg.wait_for_timeout(500)
        pg.screenshot(path=str(out / "shots" / f"{nome}.png"), full_page=full); pg.close()
    # Componentes da tela e checagens por componente (componentes.py, mesma pasta deste script)
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import componentes
    componentes.passe(ctx, src, out, tw_css, viewports=(("mobile", 390, 844),) if MODO == "mobile" else (("desktop", 1440, 900), ("mobile", 390, 844)))
    import inventario   # widgets da tela, para o consistencia.py comparar entre telas
    res["inventario"] = inventario.varrer(ctx, src, out, tw_css, ("mobile", 390, 844) if MODO == "mobile" else ("desktop", 1440, 900))
    if MODO == "mobile":
        # larguras de celular menores e maiores, e paisagem: só transbordo e alvos de toque
        res["larguras"] = {}
        for (w, h, nome) in ((320, 568, "320"), (360, 800, "360"), (430, 932, "430"), (844, 390, "paisagem-844x390")):
            pg = ctx.new_page(); pg.set_viewport_size({"width": w, "height": h})
            try: pg.goto(src.as_uri(), wait_until="networkidle", timeout=45000)
            except Exception: pg.goto(src.as_uri(), wait_until="load", timeout=45000)
            if tw_css: pg.add_style_tag(content=tw_css)
            pg.evaluate("() => document.fonts.ready"); pg.wait_for_timeout(400)
            pg.screenshot(path=str(out / "shots" / f"larg-{nome}.png"))
            r = pg.evaluate(JS); res["larguras"][nome] = {k: r[k] for k in ("overflow_x", "alvos_toque_pequenos", "alvos_menor_24", "texto_menor_12px")}
            res["larguras"][nome]["largura_casca"] = pg.evaluate("() => Math.max(0, ...[...document.body.querySelectorAll('*')].filter(e => e.getBoundingClientRect().height >= 600).map(e => Math.round(e.getBoundingClientRect().width)))")
            pg.close()
        # artboard de largura fixa (390px escritos no desenho): em 430px o bloco alto da tela continua com ~390 de largura, então 320/360 não são avaliáveis
        res["largura_fixa"] = 0 < res["larguras"]["430"]["largura_casca"] <= 392
        import mobile_estados
        res["estados"] = mobile_estados.varrer(ctx, src, out, tw_css)
    b.close()
res["modo"] = MODO
res["rede"] = {"servidos_via_npm": sorted(servidos), "bloqueados": sorted(bloqueados),
               "fidelidade": "parcial" if bloqueados else "completa"}
(out / "checagens.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps({"fidelidade": res["rede"]["fidelidade"], "bloqueados": res["rede"]["bloqueados"][:5],
                  "modo": MODO, **{vp: {k: res[vp][k] for k in ("overflow_x", "alvos_toque_pequenos", "texto_menor_12px")} for vp in VPS},
                  "estados": {k: v for k, v in res.get("estados", {}).items() if k != "lista"}}, ensure_ascii=False))
