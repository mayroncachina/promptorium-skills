# temperatura.py <pasta _vl_out> [notas.json] [julgados.json]
# julgados.json (opcional): problemas que só a leitura humana/agente vê, com pontos explícitos:
#   [{"vp": "desktop", "componente": "C6", "problema": "miniatura de projeto vazia", "pontos": 20}]
#   pontos: 10 (leve), 20 (médio) ou 30 (grave); entram no mapa marcados como "julgado".
# Junta as checagens por componente (componentes-<vp>.json, feitas pelo captura.py) com os
# achados do Hallmark (lista "achados" do notas.json, ligados ao componente pela linha do
# código ou pelo texto do elemento), calcula a temperatura 0-100 de cada componente e região e
# desenha o mapa: captura em cinza + camada de calor numa rampa laranja de um matiz só.
# Saída: temperatura.json, mapa-<vp>.png (página inteira) e mapa-<vp>-colunas.png (página
# cortada em colunas, para caber numa tela ou folha), legenda inclusa.
import sys, json, re, math, pathlib
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from componentes import PESOS, ROTULOS

out = pathlib.Path(sys.argv[1])
notas = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and sys.argv[2] != "-" else {}
julgados = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else []
FAIXAS = [(0, "frio", "#fde4cf", "#1b1b1b"), (20, "morno", "#f8b07c", "#1b1b1b"), (40, "atenção", "#eb7a3c", "#1b1b1b"),
          (60, "quente", "#c4521b", "#ffffff"), (80, "crítico", "#8a3510", "#ffffff")]
HM = {"FAIL": 15, "REFLEX": 8, "WARN": 3}
CASA = {"54", "58", "63", "67"}; IGNORA = {"20", "32", "render"}
COBRE = {"40": ("contraste",), "41": ("contraste",), "26a": ("foco_invisivel", "foco_fraco", "foco_padrao"),
         "33": ("svg_sem_aria",), "10a": ("transition_all",)}
GATES_PT = {"2a": "gradiente roxo-azul", "2b": "texto em gradiente", "3": "trio de cards com ícone em quadrado", "6a": "hero dimensionado em vh",
    "7a": "preto ou branco puro fora dos tokens", "19": "copy de modelo", "26b": "sem estado :active", "29": "brilho ou vidro decorativo",
    "34": "rolagem lateral", "38iii": "palavra destacada dentro do título", "39b": "altura de controle fora do padrão", "44b": "CTA abaixo da dobra",
    "44c": "hero mal dimensionado", "44d": "sem largura máxima em telas grandes", "46a": "métrica ou prova sem fonte", "48": "cor fora dos tokens",
    "49a": "rótulo de botão quebra linha", "54": "sobretítulo acima do título", "58": "texto demais numa tela", "59": "pouco espaço entre seções",
    "63": "pontuação de modelo", "67": "rótulo em caixa alta espaçada", "71": "título colado no bloco anterior", "74": "paleta padrão do framework",
    "77": "seção estreita e sem massa", "78": "títulos de seção pequenos", "79": "vazio antes da dobra"}
FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; FONTE_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def faixa(t): return [f for f in FAIXAS if t >= f[0]][-1]
def hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def largura_do(ev):
    m = re.match(r"\[(\d+)px\]", ev or ""); return int(m.group(1)) if m else None

def alvo_hallmark(f, itens):
    ev, linha = f.get("evidence", ""), f.get("line") or 0
    comps = [i for i in itens if i["tipo"] != "região"]; regs = [i for i in itens if i["tipo"] == "região"]
    if linha > 1 and not ev.startswith("["):
        for grupo in (comps, regs):
            c = [i for i in grupo if i.get("linhas") and i["linhas"][0] <= linha <= i["linhas"][1]]
            if c: return min(c, key=lambda i: i["linhas"][1] - i["linhas"][0])
    m = re.search(r'"([^"]{3,})"', ev)
    if m:
        alvo = m.group(1).rstrip("…").strip()
        for grupo in (comps, regs):
            c = [i for i in grupo if alvo and alvo in i.get("texto", "")]
            if c: return min(c, key=lambda i: i["caixa"]["w"] * i["caixa"]["h"])
    return None

def temperatura(problemas):
    proprios = {p["tipo"] for p in problemas if p["tipo"] not in ("hallmark", "julgado")}
    t = sum(PESOS[k] for k in proprios)
    t += sum({p["det"]: p["pontos"] for p in problemas if p["tipo"] == "julgado"}.values())
    gates = {}
    for p in problemas:
        if p["tipo"] == "hallmark":
            g = p["gate"]; pts = HM["REFLEX"] if (p["grade"] == "FAIL" and g in CASA) else HM[p["grade"]]
            gates[g] = max(gates.get(g, 0), pts)
    return min(100, t + min(40, sum(gates.values())))

def resumo(problemas):
    """Um item por problema distinto, ordenado pelo peso na temperatura (depois pela contagem)."""
    por, graves = {}, sum(1 for p in problemas if p["tipo"] == "contraste_grave")
    for p in problemas:
        if p["tipo"] == "contraste_grave": continue
        if p["tipo"] == "hallmark":
            k = "Hallmark " + p["gate"] + " " + p["grade"] + (" · " + GATES_PT[p["gate"]] if p["gate"] in GATES_PT else ""); w = HM["REFLEX"] if (p["grade"] == "FAIL" and p["gate"] in CASA) else HM[p["grade"]]
        elif p["tipo"] == "julgado": k, w = "julgado: " + p["det"], p["pontos"]
        else:
            k, w = ROTULOS[p["tipo"]], PESOS[p["tipo"]]
            if p["tipo"] == "contraste" and graves: k, w = f"contraste abaixo de 4,5:1 ({graves} abaixo de 3:1)", w + PESOS["contraste_grave"]
        d = por.setdefault(k, {"problema": k, "n": 0, "peso": w, "exemplo": p["det"], "linha": p.get("linha")}); d["n"] += 1
    return sorted(por.values(), key=lambda d: (-d["peso"], -d["n"]))

resultado = {"faixas": [{"de": f[0], "nome": f[1], "cor": f[2]} for f in FAIXAS], "pesos": PESOS}
for vp in ("desktop", "mobile"):
    arq = out / f"componentes-{vp}.json"
    if not arq.exists(): continue
    d = json.load(open(arq)); itens = d["regioes"] + d["componentes"]; pagina = d["pagina"]
    for f in notas.get("achados", []):
        g, grade = f["gate"], f["grade"]
        if g in IGNORA or g.startswith("F") or grade not in HM: continue
        w = largura_do(f.get("evidence"))
        if w is not None and ((vp == "mobile") != (w <= 768)): continue
        alvo = alvo_hallmark(f, itens) or pagina
        if g in COBRE and any(p["tipo"] in COBRE[g] for p in alvo["problemas"]): continue
        alvo["problemas"].append({"tipo": "hallmark", "gate": g, "grade": grade, "det": f.get("evidence", "")[:140], "linha": f.get("line")})
    por_id = {i["id"]: i for i in itens}
    for j in julgados:
        if j.get("vp", "desktop") == vp and j["componente"] in por_id:
            por_id[j["componente"]]["problemas"].append({"tipo": "julgado", "det": j["problema"], "pontos": max(0, min(30, int(j["pontos"]))), "linha": None})
    for c in d["componentes"]: c["temp"] = temperatura(c["problemas"])
    for r in d["regioes"]:   # a região é tão quente quanto seu pior ponto: problemas próprios ou o componente mais quente
        filhos = [c["temp"] for c in d["componentes"] if c.get("regiao") == r["id"]]
        r["temp_propria"] = temperatura(r["problemas"]); r["temp"] = max([r["temp_propria"]] + filhos)
    pagina["temp"] = temperatura(pagina["problemas"])
    for i in itens + [pagina]: i["resumo"] = resumo(i["problemas"]); i["faixa"] = faixa(i.get("temp", 0))[1]
    ranking = sorted(itens, key=lambda i: (-i["temp"], i["tipo"] == "região"))
    resultado[vp] = {"viewport": d["viewport"], "foco": d.get("foco_resumo"),
                     "itens": [{k: i[k] for k in ("id", "nome", "tipo", "temp", "temp_propria", "faixa", "caixa", "linhas", "resumo") if k in i} | {"regiao": i.get("regiao")} for i in ranking],
                     "pagina": {k: pagina[k] for k in ("temp", "faixa", "resumo")}}

    # ---- desenho ----
    base = Image.open(out / f"comp-{vp}.png").convert("RGB")
    W, H = base.size; esc = W / d["viewport"].get("largura_doc", d["viewport"]["w"])  # captura = largura do documento
    cinza = ImageEnhance.Brightness(ImageOps.grayscale(base).convert("RGB")).enhance(1.12)
    cinza = Image.blend(cinza, Image.new("RGB", cinza.size, (255, 255, 255)), 0.35)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(camada)
    tam = max(14, round(W / 60)); fb = ImageFont.truetype(FONTE, tam); fr = ImageFont.truetype(FONTE, round(tam * 0.85))
    ocupados = []
    def chip(x, y, texto, fx, fonte, fora_se_menor=None):
        l, t, r_, b = dr.textbbox((0, 0), texto, font=fonte); pad = round(tam * 0.3)
        cw, ch = (r_ - l) + 2 * pad, (b - t) + 2 * pad
        if fora_se_menor is not None: y = y - ch - 6 if fora_se_menor < ch * 3 else y - ch // 2   # selo sobre a borda superior
        x, y = max(0, min(x, W - cw)), max(0, y)
        for _ in range(40):   # desce até não colidir com outro selo
            if not any(x < o[2] and x + cw > o[0] and y < o[3] and y + ch > o[1] for o in ocupados): break
            y += ch + 2
        ocupados.append((x, y, x + cw, y + ch))
        dr.rectangle([x, y, x + cw, y + ch], fill=hexrgb(fx[2]) + (255,), outline=(255, 255, 255, 255), width=1)
        dr.text((x + pad - l, y + pad - t), texto, font=fonte, fill=hexrgb(fx[3]) + (255,))
    for r in d["regioes"]:
        fx = faixa(r["temp"]); c = r["caixa"]; x0, y0 = c["x"] * esc, c["y"] * esc; x1, y1 = x0 + c["w"] * esc, y0 + c["h"] * esc
        dr.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], outline=hexrgb(fx[2]) + (255,), width=max(3, tam // 5))
    for c in sorted(d["componentes"], key=lambda c: -c["caixa"]["w"] * c["caixa"]["h"]):
        fx = faixa(c["temp"]); b = c["caixa"]; x0, y0 = b["x"] * esc, b["y"] * esc; x1, y1 = x0 + b["w"] * esc, y0 + b["h"] * esc
        alpha = 40 if c["temp"] < 20 else 95
        dr.rectangle([x0, y0, x1, y1], fill=hexrgb(fx[2]) + (alpha,), outline=hexrgb(fx[2]) + (255,), width=max(2, tam // 6))
    for r in sorted(d["regioes"], key=lambda r: r["caixa"]["y"]):
        c = r["caixa"]; nome = r["nome"] if len(r["nome"]) <= 34 else r["nome"][:33] + "…"
        chip(c["x"] * esc + 6, c["y"] * esc + 6, f'{r["id"]} {nome} · {r["temp"]}°', faixa(r["temp"]), fb)
    for c in sorted(d["componentes"], key=lambda c: (c["caixa"]["y"], c["caixa"]["x"])):
        b = c["caixa"]; chip(b["x"] * esc + 6, b["y"] * esc, f'{c["id"]} {c["temp"]}°', faixa(c["temp"]), fr, fora_se_menor=b["h"] * esc)
    if W > d["viewport"]["w"] * esc + 2:   # página mais larga que a tela: marca onde a tela termina
        xv = d["viewport"]["w"] * esc
        dr.rectangle([xv, 0, W, H], fill=(138, 53, 16, 40)); dr.line([xv, 0, xv, H], fill=(138, 53, 16, 255), width=max(3, tam // 4))
        chip(xv + 6, 4, f'fim da tela ({d["viewport"]["w"]}px): tudo à direita transborda', FAIXAS[4], fr)
    mapa = Image.alpha_composite(cinza.convert("RGBA"), camada).convert("RGB")
    # legenda no topo
    alt = round(tam * 3.4); leg = Image.new("RGB", (W, alt), (255, 255, 255)); dl = ImageDraw.Draw(leg)
    dl.text((tam, round(tam * 0.4)), f"Temperatura por componente · {vp} {d['viewport']['w']}px", font=fb, fill=(27, 27, 27))
    x = tam; yb = round(tam * 1.9)
    for f in FAIXAS:
        rot = f"{f[0]}–{f[0] + 19 if f[0] < 80 else 100}° {f[1]}"
        dl.rectangle([x, yb, x + tam, yb + tam], fill=hexrgb(f[2]), outline=(120, 120, 120))
        dl.text((x + tam + 6, yb - 1), rot, font=fr, fill=(60, 60, 60)); x += tam + 16 + dl.textlength(rot, font=fr)
    cheio = Image.new("RGB", (W, H + alt), (255, 255, 255)); cheio.paste(leg, (0, 0)); cheio.paste(mapa, (0, alt))
    cheio.save(out / f"mapa-{vp}.png")
    # versão em colunas: corta a página perto das bordas de região
    ncol = max(1, math.ceil(H / (W * 2.0))) if vp == "desktop" else min(4, max(1, math.ceil(H / (W * 2.3))))
    if ncol > 1:
        bordas = sorted({r["caixa"]["y"] * esc for r in d["regioes"]} | {H})
        cortes, alvo_h = [0], H / ncol
        for k in range(1, ncol):
            ideal = alvo_h * k; perto = min(bordas, key=lambda b: abs(b - ideal)) if bordas else ideal
            cortes.append(perto if abs(perto - ideal) < 0.2 * alvo_h else ideal)   # borda de região só se estiver perto
        cortes = sorted(set(round(c) for c in cortes)) + [H]
        partes = [mapa.crop((0, cortes[i], W, cortes[i + 1])) for i in range(len(cortes) - 1) if cortes[i + 1] - cortes[i] > 20]
        gap = tam; hmax = max(p.size[1] for p in partes)
        col = Image.new("RGB", (len(partes) * W + (len(partes) - 1) * gap, hmax + alt), (255, 255, 255))
        col.paste(leg.crop((0, 0, min(W, col.size[0]), alt)), (0, 0))
        for i, p in enumerate(partes): col.paste(p, (i * (W + gap), alt))
        col.save(out / f"mapa-{vp}-colunas.png")
    else:
        cheio.save(out / f"mapa-{vp}-colunas.png")

(out / "temperatura.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
for vp in ("desktop", "mobile"):
    if vp in resultado:
        top = resultado[vp]["itens"][:6]
        print(vp, " | ".join(f'{i["id"]} {i["nome"][:28]} {i["temp"]}°' for i in top), "| página", resultado[vp]["pagina"]["temp"], "°")
