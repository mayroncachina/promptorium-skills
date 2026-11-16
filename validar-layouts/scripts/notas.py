# notas.py <sloplint.json|-> <checagens.json|-> <gates.md> [ajustes.json] > notas.json
# Use "-" quando não houver código (só PNG/PDF): aí ajustes.json traz "notas_visuais".
# Nota mecânica por dimensão (0-10) a partir dos gates do Hallmark e das checagens
# ui-ux-pro-max; com ajustes.json aplica a parte julgada e calcula a nota geral (0-100).
import sys, json, re, collections

sl = json.load(open(sys.argv[1])) if sys.argv[1] != "-" else {"findings": [], "summary": {}}
ck = json.load(open(sys.argv[2])) if sys.argv[2] != "-" else {}; gates_md = open(sys.argv[3]).read()
aj = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
# O sloplint renderiza também o arquivo cru, que no workspace fica sem CSS de CDN. Quando o
# snapshot (_vl_render.html via --url) rodou, os achados de render do arquivo cru são descartados.
if any(str(f.get("file", "")).startswith("http") for f in sl["findings"]):
    sl["findings"] = [f for f in sl["findings"] if str(f.get("file", "")).startswith("http")
                      or not (f["gate"] == "render" or str(f.get("evidence", "")).startswith("["))]

# Artboard do Claude Design (renderizado como <nome>.vl.html, mesmas linhas do .dc.html): o formato pede
# as cores fixas escritas direto no artboard, para pintar durante o streaming, então "cor literal fora
# dos tokens" (gate 48) não se aplica. Meta viewport e meta description são do editor, não do artboard.
import pathlib as _pl
DC = any(str(f.get("file", "")).endswith(".vl.html") for f in sl["findings"]) or \
     (sys.argv[1] != "-" and any(_pl.Path(sys.argv[1]).resolve().parent.parent.glob("*.vl.html")))
if DC:
    sl["findings"] = [f for f in sl["findings"] if f["gate"] != "48"]
    for f in sl["findings"]:
        if str(f.get("file", "")).endswith(".vl.html"): f["file"] = f["file"][: -len(".vl.html")] + ".dc.html"

import os
MODO = ck.get("modo", "desktop")   # "mobile": tela de app, medida só no celular (captura.py --modo mobile)
ALVO = 48 if os.environ.get("VL_ALVO") == "48" else 44   # 48 = Material/Flutter/Android (dp); 44 = iOS (pt)
PESOS = {"acessibilidade": 20, "layout_responsivo": 15, "tipografia_cor": 15, "hierarquia": 15,
         "originalidade": 15, "interacao_estados": 10, "conteudo_completude": 10}
if MODO == "mobile":   # app: toque, navegação e estados pesam mais; originalidade e hierarquia de landing pesam menos
    PESOS = {"acessibilidade": 20, "layout_responsivo": 15, "tipografia_cor": 10, "hierarquia": 10,
             "originalidade": 10, "interacao_estados": 25, "conteudo_completude": 10}
SECAO = {"Colour": "tipografia_cor", "Type": "tipografia_cor", "Structure": "layout_responsivo",
         "Chrome": "originalidade", "Motion": "interacao_estados", "Assets": "acessibilidade"}
FORCA = {"26a": "acessibilidade", "26b": "acessibilidade", "27": "acessibilidade", "62": "acessibilidade",
         "40": "acessibilidade", "41": "acessibilidade", "44b": "hierarquia", "58": "hierarquia",
         "46a": "conteudo_completude", "46b": "conteudo_completude", "19": "conteudo_completude", "69": "conteudo_completude"}
HOUSE = {"54", "58", "63", "67"}  # regras da casa do Hallmark (mais rígidas que o mercado): pesam como Reflex
IGNORA = {"20", "32"}  # carimbo e livro-razão do próprio Hallmark: não se aplicam a layouts de terceiros
if MODO == "mobile":   # gates de landing page (hero, CTA na dobra, largura máxima, vazio antes da dobra, ritmo de seções)
    IGNORA |= {"44b", "44c", "44d", "6a", "59", "71", "77", "78", "79"}
    import re as _re
    def _largura(f):
        m = _re.match(r"\[(\d+)px\]", f.get("evidence") or ""); return int(m.group(1)) if m else None
    # o sloplint também renderiza em 1280/1440/1920 e em 320/375. Num artboard de celular, achado medido em largura de desktop
    # (rolagem lateral, texto sob outro elemento, altura de controle...) é efeito de esticar o artboard, não defeito; só o contraste
    # do anel de foco (26a) não depende da largura. Rolagem lateral em 320/375 de artboard de largura fixa entra como "não verificado".
    LARGURA_LIVRE = {"26a"}
    sl["findings"] = [f for f in sl["findings"] if not (
        ((_largura(f) or 0) > 500 and f["gate"] not in LARGURA_LIVRE)
        or (f["gate"] == "34" and ((ck.get("largura_fixa") and (_largura(f) or 999) <= 430) or "overflow-x" in (f.get("evidence") or ""))))]

mapa, sec = {}, None
for line in gates_md.splitlines():
    if line.startswith("### "): sec = line[4:].split()[0]
    m = re.match(r"^\| ([0-9]+[a-z]*) \|", line)
    if m and sec in SECAO: mapa[m.group(1)] = SECAO[sec]
mapa.update(FORCA)

def dim_do_gate(g):
    if g.startswith("F"): return None              # Finish: vira sugestão, não desconta
    return mapa.get(g) or mapa.get(re.sub(r"[a-z]+$", "", g))

PEN = {"FAIL": 1.5, "REFLEX": 0.75, "WARN": 0.25}
desc = collections.defaultdict(float); motivos = collections.defaultdict(list)
por_gate = collections.Counter((f["gate"], f["grade"]) for f in sl["findings"])
for (g, grade), n in por_gate.items():
    if g in IGNORA or grade not in PEN: continue
    d = dim_do_gate(g)
    if g == "render": continue
    if not d: continue
    if grade == "WARN" and g in aj.get("warns_descartados", []): continue
    p = PEN["REFLEX" if grade == "FAIL" and g in HOUSE else grade] + min(0.5, 0.1 * (n - 1))
    desc[d] += p; motivos[d].append(f"Hallmark {g} {grade} x{n} (-{p:.2f})")

def chk(d, cond, pen, txt):
    if cond: desc[d] += pen; motivos[d].append(f"{txt} (-{pen})")
dk, mb = ck.get("desktop", {}), ck.get("mobile", {})
if MODO == "mobile": dk = mb   # só existe a medição do celular
chk("acessibilidade", dk.get("img_sem_alt", 0) > 0, 1, f"{dk.get('img_sem_alt')} imagem(ns) sem alt")
chk("acessibilidade", dk.get("campos_sem_label", 0) > 0, 1, f"{dk.get('campos_sem_label')} campo(s) sem label")
chk("acessibilidade", dk.get("botoes_icone_sem_nome", 0) > 0, 1, f"{dk.get('botoes_icone_sem_nome')} botão(ões) só-ícone sem nome")
chk("acessibilidade", dk.get("div_clicavel", 0) > 0, 1, "div/span clicável no lugar de botão")
chk("acessibilidade", not dk.get("lang"), 0.5, "sem atributo lang")
chk("acessibilidade", dk.get("h1", 1) != 1 or dk.get("saltos_de_titulo", 0) > 0, 0.5, f"estrutura de títulos (h1={dk.get('h1')}, saltos={dk.get('saltos_de_titulo')})")
chk("layout_responsivo", mb.get("overflow_x"), 2, "rolagem horizontal no mobile (390px)")
chk("layout_responsivo", not DC and not dk.get("viewport_meta", True), 1.5, "sem meta viewport")
chk("tipografia_cor", dk.get("texto_menor_12px", 0) > 0, 1, f"{dk.get('texto_menor_12px')} texto(s) < 12px")
n24 = mb.get("alvos_menor_24", 0)
nT = max(0, (mb.get("alvos_menor_48", 0) if ALVO == 48 else mb.get("alvos_toque_pequenos", 0)) - n24)
chk("interacao_estados", n24 > 0, min(2, 0.5 * n24), f"{n24} alvo(s) de toque < 24px no mobile (mínimo WCAG 2.2)")
chk("interacao_estados", nT > 0, min(1.5 if MODO == "mobile" else 0.5, 0.25 * nT if MODO == "mobile" else 0.1 * nT), f"{nT} alvo(s) de toque entre 24px e {ALVO - 1}px no mobile (recomendado {ALVO})")
if MODO == "mobile":
    import pathlib as _p
    cm = _p.Path(sys.argv[2]).resolve().parent / "componentes-mobile.json"
    tipos = collections.Counter()
    if cm.exists():
        d_ = json.load(open(cm))
        for it in d_["regioes"] + d_["componentes"] + [d_["pagina"]]:
            for p in it["problemas"]: tipos[p["tipo"]] += 1
    chk("interacao_estados", tipos["barra_5"] > 0, 1.5, "barra de navegação com mais de 5 itens")
    chk("interacao_estados", tipos["gesto_so"] > 0, min(2, 1.0 * tipos["gesto_so"]), f"{tipos['gesto_so']} carrossel(is) só por gesto, sem botão (WCAG 2.5.7)")
    chk("interacao_estados", tipos["campo_tipo"] > 0, min(1.5, 0.5 * tipos["campo_tipo"]), f"{tipos['campo_tipo']} campo(s) sem inputmode/type adequado")
    chk("interacao_estados", tipos["campo_fonte"] > 0, min(1.5, 0.5 * tipos["campo_fonte"]), f"{tipos['campo_fonte']} campo(s) com texto menor que 16px (zoom automático no iOS)")
    chk("interacao_estados", tipos["alvo_junto"] > 0, min(2, 0.5 * tipos["alvo_junto"]), f"{tipos['alvo_junto']} alvo(s) de toque a menos de 8px de outro")
    chk("layout_responsivo", tipos["barra_altura"] > 0, min(1.5, 0.75 * tipos["barra_altura"]), f"{tipos['barra_altura']} barra(s) de navegação fora da altura usual")
    es = ck.get("estados", {})
    chk("layout_responsivo", es.get("cobertos", 0) > 0, min(3, 1.5 * es.get("cobertos", 0)), f"{es.get('cobertos')} elemento(s) coberto(s) por outro (botão flutuante sobre a navegação, item atrás de barra fixa)")
    chk("layout_responsivo", es.get("transbordo", 0) > 0, min(2, 1.0 * es.get("transbordo", 0)), f"rolagem lateral em {es.get('transbordo')} estado(s) da tela")
    lar = [] if ck.get("largura_fixa") else [k for k, v in ck.get("larguras", {}).items() if v.get("overflow_x")]   # artboard de largura fixa: 320/360 não se aplicam
    chk("layout_responsivo", len(lar) > 0, min(3, 1.5 * len(lar)), "transbordo em: " + ", ".join(lar))
    chk("conteudo_completude", len(es.get("sem_efeito", [])) > 0, min(2, 0.5 * len(es.get("sem_efeito", []))), "controle(s) que não mudam nada ao toque: " + ", ".join(es.get("sem_efeito", [])[:4]))
import pathlib as _q
_cf = _q.Path(sys.argv[2]).resolve().parent / "consistencia.json" if sys.argv[2] != "-" else None
if _cf and _cf.exists():   # widgets diferentes entre telas (consistencia.py)
    _pr = json.load(open(_cf))["problemas"]; _na = sum(1 for x in _pr if x["tipo"].startswith("acao")); _no = len(_pr) - _na
    chk("interacao_estados", _na > 0, min(2.5, 0.5 * _na), f"{_na} botão(ões) de ação com tipo, tamanho ou forma diferente do padrão do conjunto")
    chk("hierarquia", _no > 0, min(2, 0.4 * _no), f"{_no} widget(s) diferente(s) do padrão do conjunto (cartão, campo, cabeçalho, navegação...)")
chk("originalidade", dk.get("emoji_em_texto", 0) > 0, 1, "emoji usado como ícone/enfeite")
chk("conteudo_completude", not dk.get("title"), 0.5, "sem <title>")
chk("conteudo_completude", not DC and not dk.get("meta_description", True), 0.5, "sem meta description")
chk("conteudo_completude", dk.get("erros_console"), 1, "erros no console")

out = {"dimensoes": {}, "pesos": PESOS, "fidelidade_render": ck.get("rede", {}).get("fidelidade")}
eixos = aj.get("eixos_hallmark", {})  # P H E S R de 1 a 5
def eixo10(*ks):
    v = [eixos[k] for k in ks if k in eixos]
    return (sum(v) / len(v) - 1) * 2.5 if v else None
for d in PESOS:
    vis = aj.get("notas_visuais", {}).get(d)
    mec = float(vis) if vis is not None else max(0.0, 10 - desc[d])
    item = {"mecanica": round(mec, 1), "motivos": motivos[d]}
    jul = {"hierarquia": eixo10("H"), "originalidade": eixo10("P", "S", "R")}.get(d)
    a = aj.get("ajustes", {}).get(d, {})
    nota = mec if jul is None else 0.5 * mec + 0.5 * jul
    nota = max(0.0, min(10.0, nota + max(-2, min(2, a.get("delta", 0)))))
    item.update({"julgada": None if jul is None else round(jul, 1), "ajuste": a, "nota": round(nota, 1)})
    out["dimensoes"][d] = item
geral = sum(out["dimensoes"][d]["nota"] * p for d, p in PESOS.items()) / 10
floor_a11y = any(f["grade"] == "FAIL" and f["gate"] in ("40", "41", "26a", "27") for f in sl["findings"])
status = ("Pronto para entregar" if geral >= 85 else "Ajustes pontuais" if geral >= 70
          else "Revisão necessária" if geral >= 50 else "Refazer")
if floor_a11y and status == "Pronto para entregar": status = "Ajustes pontuais"
out.update({"geral": round(geral), "status": status, "bloqueio_acessibilidade": floor_a11y,
            "contagem_hallmark": {g: sum(1 for f in sl["findings"] if f["grade"] == g) for g in ("FAIL", "REFLEX", "WARN")},
            "achados": sl["findings"], "julgamento_pendente": not aj,
            "modo_audit": MODO, "modo": "visual (sem código)" if sys.argv[1] == "-" else ("artboard Claude Design + render local" if DC else "código + render")})
print(json.dumps(out, ensure_ascii=False, indent=1))
