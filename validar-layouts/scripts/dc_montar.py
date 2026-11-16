# dc_montar.py <pasta_project> [mobile|desktop]
# O 2º argumento força o modo de todos os artboards; sem ele, o modo é automático: artboard de até 500px de largura = mobile.
# Prepara os artboards .dc.html de um canvas do Claude Design para a auditoria. Para cada artboard
# (os de canvas.json, ou todo .dc.html se não houver canvas.json) grava <nome>.vl.html ao lado do
# original: o mesmo texto, linha por linha, com o <script src="./support.js"> do editor trocado, NA
# MESMA LINHA, pelo runtime local (dc_lite.js) e pelo registro dos arquivos irmãos usados em
# <dc-import>. As linhas ficam iguais às do .dc.html, então os achados citam a linha do original.
# Saída: _vl_artboards.json na pasta e a mesma lista no stdout.
import sys, json, re, shutil, pathlib

T = pathlib.Path(__file__).resolve().parent
proj = pathlib.Path(sys.argv[1]).resolve()
FORCA = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in ('mobile', 'desktop') else None
fontes = {p.relative_to(proj).as_posix(): p.read_text(errors="replace")
          for p in sorted(proj.rglob("*.dc.html")) if not p.name.startswith("_vl_")}
if not fontes: sys.exit("nenhum .dc.html em " + str(proj))
shutil.copy(T / "dc_lite.js", proj / "_vl_dc.js")
(proj / "_vl_dc_src.js").write_text("window.__DC_SRC = " + json.dumps(fontes, ensure_ascii=False) + ";\n")

canvas = {}
if (proj / "canvas.json").exists():
    try: canvas = json.loads((proj / "canvas.json").read_text())
    except Exception: canvas = {}
boards = canvas.get("boards") or {}
ordem = [b for b in (canvas.get("order") or list(boards)) if b in fontes] or \
        [f for f in fontes if not f.startswith("ds/")]

saida = []
for rel in ordem:
    texto = fontes[rel]
    sobe = "../" * rel.count("/")
    tags = (f'<script>window.__DC_FILE={json.dumps(rel)}</script>'
            f'<script src="{sobe}_vl_dc_src.js"></script><script src="{sobe}_vl_dc.js"></script>')
    novo, n = re.subn(r'<script\b[^>]*\bsrc="[^"]*support\.js"[^>]*>\s*</script>', lambda m: tags, texto, count=1, flags=re.I)
    if not n:   # sem a tag do editor: entra na linha do <head>, sem criar linhas novas
        novo, n = re.subn(r"(<head\b[^>]*>)", lambda m: m.group(1) + tags, texto, count=1, flags=re.I)
    if not n: novo = tags + texto
    destino = proj / (rel[: -len(".dc.html")] + ".vl.html")
    destino.write_text(novo)
    b = boards.get(rel, {})
    saida.append({"artboard": rel, "html": str(destino), "titulo": b.get("title") or rel,
                  "w": b.get("w"), "h": b.get("h"), "pagina": b.get("expand") == "fill",
                  "interativo": bool(b.get("is_interactive")),
                  "celular": bool(b.get("w")) and b.get("w") <= 500,
                  "modo": FORCA or ("mobile" if (b.get("w") and b.get("w") <= 500) else "desktop"),
                  "imports": sorted(set(re.findall(r'<dc-import\b[^>]*\bname="([^"]+)"', texto)))})
(proj / "_vl_artboards.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1))
print(json.dumps(saida, ensure_ascii=False, indent=1))
