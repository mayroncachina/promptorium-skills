# Auditoria Hallmark

Use o verbo **audit** do Hallmark (o usuário nomeou o Hallmark ao pedir esta skill). Leia `hallmark/skills/hallmark/references/redesign.md` (o parágrafo do `audit`) e `references/gates.md` § 1, § 3, § 4 e § 5.

1. **sloplint**: estático no código do artboard, render no snapshot servido localmente:
   ```bash
   T=/tmp/vl-tools; P="<TMP>/project"; O="<TMP>/out/<S>"; PORT=$((8700 + RANDOM % 200))
   (python3 -m http.server $PORT --bind 127.0.0.1 --directory "$P" >/dev/null 2>&1 &); sleep 1
   HALLMARK_PUPPETEER=$T CHROME_PATH=$T/chrome node $T/hallmark/skills/hallmark/scripts/sloplint.mjs \
     "$P/<S>.vl.html" --url "http://127.0.0.1:$PORT/_vl_render.html" --json > "$O/sloplint.json"
   ```
   **Telas de app** (dashboard, painel, formulário interno, ou quando o usuário passou `app`): acrescente `--scope app`, para o sloplint não aplicar regras de landing page (orçamento de palavras, ritmo de seções, dobra do hero).
   Saída diferente de 0 é normal (há FAILs). Se `summary.render` não for `ran`, siga só com o estático e registre o motivo. O sloplint também renderiza o arquivo cru, sem o runtime: o `notas.py` descarta esses achados de render e devolve a lista limpa em `achados` no `notas.json`, já com o nome `.dc.html` no lugar do `.vl.html` (as linhas são as mesmas). **Use essa lista no relatório, não o `sloplint.json` cru.** Pelo mesmo motivo, **ignore `.hallmark/shots/`**: as telas certas ficam em `<TMP>/out/<S>/shots/` (dobras em 1280, 1440 e 1920; páginas inteiras em 1440 e 375).
   **Regras do formato do Claude Design** que o `notas.py` já aplica: o gate 48 (cor literal fora dos tokens) não conta, porque o formato pede as cores escritas direto no artboard; meta viewport e meta description não contam, porque são do editor.
2. **WARNs**: confirme ou descarte cada um olhando o código e os screenshots. Os descartados vão em `warns_descartados` no `ajustes.json`.
3. **Gates julgados** (classe J e R/J, e as metades julgadas de M/R) e **cláusulas julgadas** do § 5: avalie sobre os screenshots.
4. **Eixos de crítica** do § 3: dê de 1 a 5 em **P**hilosophy, **H**ierarchy, **E**xecution, **S**pecificity e **R**estraint (Variety não se aplica: depende do histórico de builds do Hallmark). Use as descrições da tabela como régua e justifique cada nota em uma linha.
5. **Revisão com contexto limpo** (Hallmark § 6): se a ferramenta Agent existir, rode um subagente por artboard (em paralelo, num único bloco) com o pedido: *"Leia `/tmp/vl-tools/hallmark/skills/hallmark/references/review-finish.md` e siga-o. Entradas: <caminhos de <TMP>/out/<S>/shots/*.png e <TMP>/out/<S>/mobile-dobra.png>, <caminho do .dc.html>. Ignore .hallmark/shots (capturas sem CSS). Não há stamp nem log do Hallmark: ignore entradas que dependem deles. É um artboard do Claude Design: cores escritas direto no artboard são regra do formato. Não altere arquivos. Responda em inglês, no formato do arquivo."* Não passe suas conclusões. Use os achados dele como segunda leitura: o que ele aponta e você não tinha, verifique e inclua (também no `julgados.json` da seção 6b). Se ele responder `recapture`, verifique o motivo, corrija a captura e rode a revisão de novo; nunca aproveite uma revisão feita sobre telas erradas.
6. **Profundidade recomendada**: diga qual é a profundidade mais leve do Hallmark que resolve os achados (`polish`, `restyle` ou `full`) e como pedir a correção com esta skill (`/validar-layouts <link> corrigir 80 polish` ou `restyle`); `full` fica fora do ciclo.

Ignore os gates 20 (carimbo do Hallmark) e 32 (livro-razão): não se aplicam a layouts que o Hallmark não construiu; o `notas.py` já os ignora.


## No modo mobile

Rode o sloplint **sempre com `--scope app`**. Os gates de landing page (44b CTA abaixo da dobra, 44c e 6a hero, 44d largura máxima, 59, 71, 77, 78, 79) não contam: o `notas.py` já os ignora. As telas para a revisão de contexto limpo são `shots/index-375.png`, `index-390.png`, `index-360.png`, `index-430.png`, `larg-*.png` e `estados/*.png`. Nos eixos de crítica, **H** (Hierarchy) é a clareza de qual é a ação principal da tela e de onde está a navegação. Detalhes em [10-modo-mobile.md](10-modo-mobile.md).
