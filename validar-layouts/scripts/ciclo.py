# ciclo.py: controla o modo correção (avaliar -> corrigir -> reavaliar).
#   ciclo.py iniciar  <pasta_layout> <arquivo_original>        copia a pasta do original (.html ou artboard .dc.html) para <pasta_layout>/v0/
#   ciclo.py avaliar  <pasta_versao> [--scope app]              captura, sloplint, notas e temperatura mecânicos
#   ciclo.py fechar   <pasta_versao> [--meta 80]                notas finais com ajustes.json/julgados.json do avaliador
#                                                               independente, histórico e decisão de parada
#   ciclo.py nova     <pasta_layout>                            cria v<n+1> a partir da última versão aceita
# Cada versão fica em <pasta_layout>/vN/ (código) e vN/_vl_out/ (medições). O original nunca é alterado.
import sys, json, shutil, subprocess, pathlib, socket, time, difflib

T = pathlib.Path("/tmp/vl-tools")            # ferramentas externas (Hallmark, ui-ux-pro-max, node_modules)
S = pathlib.Path(__file__).resolve().parent  # scripts desta skill
MODO = None                                  # "mobile" ou "desktop" força o modo; None = automático (pela largura do artboard)
CRITICOS = {"40", "41", "26a", "27", "34"}     # contraste, foco, movimento reduzido, rolagem lateral
MAX_RODADAS, GANHO_MIN, QUEDA_DIM = 3, 3, 1.0

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

def entrada(v):
    if (v / "entrada.txt").exists(): return (v / "entrada.txt").read_text().strip()
    hs = sorted(p.name for p in v.glob("*.html") if not p.name.startswith("_vl_") and not p.name.endswith(".vl.html"))
    return "index.html" if "index.html" in hs else hs[0]

def renderizavel(v):
    """Arquivo que o navegador abre: artboard .dc.html passa pelo dc_montar (gera <nome>.vl.html)."""
    E = entrada(v)
    if not E.endswith(".dc.html"): return E
    r = run([sys.executable, str(S / "dc_montar.py"), str(v)] + ([MODO] if MODO else []))
    if r.returncode: sys.exit("dc_montar falhou:\n" + r.stderr[-2000:])
    return E[: -len(".dc.html")] + ".vl.html"

def avaliar(v, scope=None):
    v = v.resolve(); E = renderizavel(v); O = v / "_vl_out"; O.mkdir(exist_ok=True)
    r = run([sys.executable, str(S / "captura.py"), str(v / E), str(O)] + (["--modo", MODO] if MODO else []), timeout=900)
    if r.returncode: sys.exit("captura falhou:\n" + r.stderr[-2000:])
    cons = [sys.executable, str(S / "consistencia.py"), "--alvo", str(O / "inventario.json")]
    if "--contra" in sys.argv: cons += [x for p in pathlib.Path(sys.argv[sys.argv.index("--contra") + 1]).glob("*.json") for x in ("--contra", str(p))]
    if "--exceto" in sys.argv: cons += ["--exceto", sys.argv[sys.argv.index("--exceto") + 1]]
    run(cons)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(v)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        cmd = ["node", str(T / "hallmark/skills/hallmark/scripts/sloplint.mjs"), str(v / E),
               "--url", f"http://127.0.0.1:{port}/_vl_render.html", "--json"] + (["--scope", "app"] if scope == "app" else [])
        r = run(cmd, timeout=600, env={**__import__("os").environ, "HALLMARK_PUPPETEER": str(T), "CHROME_PATH": str(T / "chrome")})
        (O / "sloplint.json").write_text(r.stdout)
    finally:
        srv.terminate()
    gates = T / "hallmark/skills/hallmark/references/gates.md"
    (O / "notas-mecanicas.json").write_text(run([sys.executable, str(S / "notas.py"), str(O / "sloplint.json"), str(O / "checagens.json"), str(gates)]).stdout)
    run([sys.executable, str(S / "temperatura.py"), str(O), str(O / "notas-mecanicas.json")])
    (O / "escopo.txt").write_text(scope or "page")
    n = json.load(open(O / "notas-mecanicas.json"))
    print(json.dumps({"versao": v.name, "mecanica": {k: d["mecanica"] for k, d in n["dimensoes"].items()},
                      "hallmark": n["contagem_hallmark"], "render": json.load(open(O / "sloplint.json"))["summary"].get("render")}, ensure_ascii=False))

def gates_fail(n):
    return sorted({f["gate"] for f in n.get("achados", []) if f["grade"] == "FAIL"})

def fechar(v, meta=80):
    v = v.resolve(); O = v / "_vl_out"; raiz = v.parent
    gates = T / "hallmark/skills/hallmark/references/gates.md"
    aj = O / "ajustes.json"
    if not aj.exists(): sys.exit("falta _vl_out/ajustes.json do avaliador independente")
    n = json.loads(run([sys.executable, str(S / "notas.py"), str(O / "sloplint.json"), str(O / "checagens.json"), str(gates), str(aj)]).stdout)
    (O / "notas.json").write_text(json.dumps(n, ensure_ascii=False, indent=1))
    arg_j = [str(O / "julgados.json")] if (O / "julgados.json").exists() else []
    run([sys.executable, str(S / "temperatura.py"), str(O), str(O / "notas.json")] + arg_j)
    tp = json.load(open(O / "temperatura.json"))
    VP = "desktop" if "desktop" in tp else "mobile"   # modo mobile só mede o celular
    reg = {"versao": v.name, "geral": n["geral"], "status": n["status"],
           "dims": {k: d["nota"] for k, d in n["dimensoes"].items()},
           "mec": {k: d["mecanica"] for k, d in n["dimensoes"].items()},
           "criticos": sorted(set(gates_fail(n)) & CRITICOS), "fails": gates_fail(n),
           "temp_max": max([i["temp"] for i in tp[VP]["itens"]] or [0]),
           "temp_media": round(sum(i["temp"] for i in tp[VP]["itens"] if i["tipo"] != "região") /
                               max(1, sum(1 for i in tp[VP]["itens"] if i["tipo"] != "região")), 1)}
    hist_f = raiz / "historico.json"
    hist = json.load(open(hist_f)) if hist_f.exists() else []
    hist = [h for h in hist if h["versao"] != v.name] + [reg]
    hist.sort(key=lambda h: int(h["versao"][1:]))
    aceitas = [h for h in hist if h.get("decisao") != "revertida"]
    ant = aceitas[-2] if len(aceitas) > 1 else None
    n_rod = int(v.name[1:])
    if ant is None:
        dec = "continuar" if (reg["geral"] < meta or reg["criticos"]) else "meta atingida"
    else:
        # regressão = cai a nota geral, aparece crítico novo ou cai a parte MECÂNICA de uma dimensão;
        # queda só na parte julgada (variação entre avaliações) vira alerta, não reverte
        quedas = [k for k in reg["mec"] if reg["mec"][k] < ant.get("mec", ant["dims"])[k] - QUEDA_DIM]
        reg["alertas"] = [f"{k}: julgamento caiu {ant['dims'][k]}→{reg['dims'][k]}" for k in reg["dims"]
                          if k not in quedas and reg["dims"][k] < ant["dims"][k] - QUEDA_DIM]
        novos = sorted(set(reg["fails"]) - set(ant["fails"]))
        if reg["geral"] < ant["geral"] or quedas or (set(reg["criticos"]) - set(ant["criticos"])):
            dec = "revertida"; reg["motivo"] = f"regressão: geral {ant['geral']}→{reg['geral']}; dimensões cuja parte mecânica caiu: {quedas or 'nenhuma'}; FAILs novos: {novos or 'nenhum'}"
        elif reg["geral"] >= meta and not reg["criticos"]:
            dec = "meta atingida"
        elif n_rod >= MAX_RODADAS:
            dec = "limite de rodadas"
        elif reg["geral"] - ant["geral"] < GANHO_MIN:
            dec = "estagnou"; reg["motivo"] = f"ganho de {reg['geral'] - ant['geral']} ponto(s), abaixo de {GANHO_MIN}"
        else:
            dec = "continuar"
        reg["novos_fails"] = novos
    reg["decisao"] = dec
    hist = [h if h["versao"] != v.name else reg for h in hist]
    hist_f.write_text(json.dumps(hist, ensure_ascii=False, indent=1))
    if n_rod > 0:   # diff contra o original
        E = entrada(v); a = (raiz / "v0" / E).read_text().splitlines(); b = (v / E).read_text().splitlines()
        (O / "diff-v0.patch").write_text("\n".join(difflib.unified_diff(a, b, f"v0/{E}", f"{v.name}/{E}", lineterm="")))
    print(json.dumps(reg, ensure_ascii=False))

def nova(raiz):
    raiz = raiz.resolve(); hist = json.load(open(raiz / "historico.json"))
    aceita = [h for h in hist if h["decisao"] != "revertida"][-1]["versao"]
    n = max(int(h["versao"][1:]) for h in hist) + 1
    dst = raiz / f"v{n}"
    shutil.copytree(raiz / aceita, dst, ignore=shutil.ignore_patterns("_vl_*", ".hallmark", "*.vl.html"))
    print(dst)

if __name__ == "__main__":
    cmd, alvo = sys.argv[1], pathlib.Path(sys.argv[2])
    if "--modo" in sys.argv: MODO = sys.argv[sys.argv.index("--modo") + 1]
    if cmd == "iniciar":
        orig = pathlib.Path(sys.argv[3]); (alvo / "v0").mkdir(parents=True, exist_ok=True)
        for p in orig.parent.iterdir():   # copia a pasta do layout (assets relativos)
            if p.name.startswith(("_vl_", ".hallmark")) or p.name.endswith(".vl.html"): continue
            (shutil.copytree if p.is_dir() else shutil.copy2)(p, alvo / "v0" / p.name)
        (alvo / "v0" / "entrada.txt").write_text(orig.name)
        print(alvo / "v0")
    elif cmd == "avaliar": avaliar(alvo, "app" if "--scope" in sys.argv and sys.argv[sys.argv.index("--scope") + 1] == "app" else None)
    elif cmd == "fechar": fechar(alvo, int(sys.argv[sys.argv.index("--meta") + 1]) if "--meta" in sys.argv else 80)
    elif cmd == "nova": nova(alvo)
