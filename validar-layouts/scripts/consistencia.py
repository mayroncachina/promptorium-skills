# consistencia.py: compara os widgets entre as telas do canvas (e dentro de cada tela).
#   consistencia.py --todos <TMP>/out [--exceto a,b]
#   consistencia.py --alvo <inventario.json> [--contra <inventario.json> ...] [--exceto a,b]
# Lê o inventario.json que o captura.py grava em cada artboard e grava consistencia.json ao lado
# (problemas daquele artboard) e consistencia-acoes.png (painel dos botões de ação, se houver Pillow).
# Regra: a referência de cada tipo de widget é o valor mais usado no conjunto; quem foge dela é alertado.
# Botões de ação do mesmo tipo (cheio, tonal, contorno, texto) têm de ter a mesma altura, forma e texto.
# Exceção: data-vl-variante="motivo" no elemento (ou num pai) e --exceto (rótulo, parte do rótulo ou tipo de widget).
import sys, json, pathlib, collections

TOL = {"h": 2, "w": 2, "raio": 2, "fonte": 1, "peso": 100, "borda": 0, "sombra": 0, "larg": 0, "filhos": 0}
NOME = {"h": "altura", "w": "largura", "raio": "forma (raio da borda)", "fonte": "tamanho do texto", "peso": "peso do texto",
        "borda": "bordas", "sombra": "sombra", "larg": "largura em relação ao bloco", "filhos": "número de itens", "variante": "tipo"}
CAMPOS = {"acao": ("variante", ["h", "raio", "fonte", "peso", "larg"]), "icone": ("aparencia", ["w", "h"]),
          "campo": ("estilo", ["h", "raio", "fonte"]), "cartao": (None, ["raio", "borda", "sombra"]),
          "atalho": (None, ["h", "raio", "borda", "sombra"]), "seletor": ("larg", ["h", "raio", "fonte"]),
          "interruptor": (None, ["w", "h"]), "cabecalho": (None, ["h", "borda", "sombra"]), "navegacao": (None, ["h", "filhos"])}
TIPO = {"acao": "botão de ação", "icone": "botão de ícone", "campo": "campo", "cartao": "cartão", "atalho": "atalho em bloco",
        "seletor": "seletor (chip/aba)", "interruptor": "interruptor", "cabecalho": "cabeçalho", "navegacao": "barra de navegação"}
GRAVES = {"variante", "h", "raio"}   # em botão de ação, tipo, altura e forma pesam mais que texto e largura

def fmt(c, v): return "pílula" if c == "raio" and v == 999 else (f"{v}px" if c in ("h", "w", "raio", "fonte") else str(v))

def moda(valores, tol):
    """Valor mais frequente (agrupando os que diferem até tol); empate fica com o primeiro visto."""
    if not valores: return None
    return max(dict.fromkeys(valores), key=lambda v: sum(1 for x in valores if abs(x - v) <= tol) if isinstance(v, (int, float)) else valores.count(v))

def perto(a, b, tol): return abs(a - b) <= tol if isinstance(a, (int, float)) and isinstance(b, (int, float)) else a == b

def excecao(it, exc):
    if it.get("declarado"): return f"declarado no desenho: {it['declarado']}"
    for t in exc:
        if t == it["kind"] or (t and t in (it.get("rotulo") or "").lower()): return f"exceção pedida: {t}"
    return None

def comparar(nome_alvo, invs, exc):
    """invs: {artboard: [itens]}; devolve (problemas do alvo, declarados do alvo, resumo por tipo)."""
    todos = [(a, it) for a, lst in invs.items() for it in lst]
    prob, decl, resumo = [], [], {}
    for kind, (agrupar, campos) in CAMPOS.items():
        grupos = collections.defaultdict(list)
        for a, it in todos:
            if it["kind"] != kind: continue
            if excecao(it, exc): continue
            grupos[it.get(agrupar) if agrupar else ""].append((a, it))
        for g, lst in grupos.items():
            ref = {c: moda([it[c] for _, it in lst if c in it], TOL[c]) for c in campos}
            quem = collections.Counter(a for a, _ in lst)
            resumo[f"{kind}:{g}" if g else kind] = {"n": len(lst), "telas": len(quem), "referencia": {c: fmt(c, v) for c, v in ref.items() if v is not None}}
            for a, it in lst:
                if a != nome_alvo: continue
                dif = [c for c in campos if c in it and ref[c] is not None and not perto(it[c], ref[c], TOL[c])]
                if not dif: continue
                graves = kind == "acao" and any(c in GRAVES for c in dif)
                prob.append({"tipo": f"{kind}_diferente", "widget": TIPO[kind], "grupo": g or None, "rotulo": it.get("rotulo"), "linha": it["linha"],
                             "gravidade": "alto" if graves else "médio", "img": it.get("img"),
                             "diferencas": {NOME[c]: {"aqui": fmt(c, it[c]), "referencia": fmt(c, ref[c])} for c in dif},
                             "mensagem": f"{TIPO[kind]}{' ' + g if g else ''} \"{it.get('rotulo') or ''}\" foge do padrão do conjunto: " +
                                         "; ".join(f"{NOME[c]} {fmt(c, it[c])} (padrão {fmt(c, ref[c])})" for c in dif)})
    # mesmo rótulo, tipo de botão diferente entre telas
    por_rot = collections.defaultdict(list)
    for a, it in todos:
        if it["kind"] == "acao" and it.get("rotulo") and not excecao(it, exc): por_rot[it["rotulo"].lower()].append((a, it))
    for rot, lst in por_rot.items():
        vs = collections.Counter(it["variante"] for _, it in lst)
        if len(vs) < 2: continue
        padrao = moda([it["variante"] for _, it in lst], 0)
        for a, it in lst:
            if a == nome_alvo and it["variante"] != padrao:
                prob.append({"tipo": "acao_rotulo_tipo", "widget": TIPO["acao"], "grupo": it["variante"], "rotulo": it["rotulo"], "linha": it["linha"], "gravidade": "alto", "img": it.get("img"),
                             "diferencas": {"tipo": {"aqui": it["variante"], "referencia": padrao}},
                             "mensagem": f"o botão \"{it['rotulo']}\" aparece como {it['variante']} aqui e como {padrao} em outras telas"})
    for a, it in todos:
        if a == nome_alvo and excecao(it, exc) and it["kind"] in CAMPOS:
            decl.append({"widget": TIPO[it["kind"]], "rotulo": it.get("rotulo"), "linha": it["linha"], "motivo": excecao(it, exc)})
    return prob, decl, resumo

def painel(invs, pasta_img, destino):
    try: from PIL import Image, ImageDraw
    except Exception: return None
    cel = []
    for a, (pasta, lst) in invs.items():
        for it in lst:
            if it.get("img") and (it["kind"] == "acao" or (it["kind"] == "icone" and it.get("aparencia") != "sem fundo")) and (pasta / it["img"]).exists():
                cel.append((a, it, Image.open(pasta / it["img"]).convert("RGB")))
    if not cel: return None
    cel.sort(key=lambda c: (c[1]["kind"], c[1].get("variante", ""), c[0]))
    W, y, x, linha_h = 1100, 8, 8, 0; fila = []
    for a, it, im in cel:
        im = im.resize((min(im.width * 2, 420), int(im.height * min(im.width * 2, 420) / im.width)))
        if x + im.width + 8 > W: x, y, linha_h = 8, y + linha_h + 24, 0
        fila.append((x, y, a, it, im)); x += im.width + 12; linha_h = max(linha_h, im.height)
    tela = Image.new("RGB", (W, y + linha_h + 30), "white"); d = ImageDraw.Draw(tela)
    for x, y, a, it, im in fila:
        tela.paste(im, (x, y)); d.text((x, y + im.height + 2), f"{a} {it['kind']}:{it.get('variante', '')} {it['w']}x{it['h']}", fill="black")
    tela.save(destino); return destino

def main(argv):
    exc = [t.strip().lower() for t in (argv[argv.index("--exceto") + 1].split(",") if "--exceto" in argv else []) if t.strip()]
    if "--todos" in argv:
        raiz = pathlib.Path(argv[argv.index("--todos") + 1]); alvos = sorted(raiz.glob("*/inventario.json"))
        refs = alvos
    else:
        alvos = [pathlib.Path(argv[argv.index("--alvo") + 1])]
        refs = alvos + [pathlib.Path(argv[i + 1]) for i, a in enumerate(argv) if a == "--contra"]
    nomes, invs, pastas = [], {}, {}
    for p in refs:
        n = p.stem if p.name != "inventario.json" else (p.parent.name if p.parent.name != "_vl_out" else p.parent.parent.name)
        if p in alvos or n not in invs:
            d = json.load(open(p)); invs[n] = d["itens"]; pastas[n] = (p.parent, d["itens"]); nomes.append((n, p))
    geral = {}
    for n, p in [(n, p) for n, p in nomes if p in alvos]:
        # se um --contra tem o mesmo nome do alvo, o alvo prevalece (já entrou primeiro)
        prob, decl, resumo = comparar(n, invs, exc)
        (p.parent / "consistencia.json").write_text(json.dumps({"artboard": n, "excecoes": exc, "problemas": prob, "declarados": decl, "resumo": resumo,
                                                               "telas_comparadas": len(invs)}, ensure_ascii=False, indent=1))
        geral[n] = {"problemas": len(prob), "acao": sum(1 for x in prob if x["tipo"].startswith("acao"))}
        img = painel(pastas, p.parent, p.parent / "consistencia-acoes.png")
    print(json.dumps({"telas": len(invs), "por_tela": geral, "excecoes": exc}, ensure_ascii=False))

if __name__ == "__main__":
    main(sys.argv[1:])
