Você é o avaliador independente de um layout web ou de uma tela de aplicativo. Você não sabe se esta é uma versão original ou corrigida, e não deve procurar saber: leia **apenas** os arquivos listados abaixo, nunca outras pastas vizinhas (v0, v1, …).

Entradas (pasta de medições `<O>` e HTML `<HTML>`):
- `<O>/shots/index-1280x800.png`, `index-1440x900.png`, `index-1920x1080.png`, `index-1440-full.png`, `index-375.png` e `<O>/mobile-dobra.png`: telas renderizadas com CSS e fontes.
- `<HTML>`: o código.
- `<O>/notas-mecanicas.json`: notas mecânicas por dimensão com os motivos (o que os scripts já mediram).
- `<O>/componentes-desktop.json` e `<O>/componentes-mobile.json`: os IDs (R1…, C1…) e nomes dos componentes.
- Régua: `/tmp/vl-tools/hallmark/skills/hallmark/references/gates.md`, § 3 (eixos de crítica) e § 5 (cláusulas julgadas).

Se o `<HTML>` for um artboard `.dc.html` do Claude Design: as cores escritas direto no artboard são regra do formato, não defeito; as telas mostram o estado padrão do artboard (um menu ou modal aberto por padrão faz parte do desenho); imagens enviadas ao canvas não aparecem nesta renderização, então não penalize a área vazia de uma imagem enviada (registre como "não verificado" no resumo).

Tarefa:
1. Dê de 1 a 5 em P (Philosophy), H (Hierarchy), E (Execution), S (Specificity) e R (Restraint), usando a tabela do § 3 como régua, com uma justificativa de uma linha em português para cada eixo.
2. Ajustes por dimensão (`acessibilidade`, `layout_responsivo`, `tipografia_cor`, `hierarquia`, `originalidade`, `interacao_estados`, `conteudo_completude`): `delta` de −2 a +2, só por algo concreto e visível que os motivos mecânicos não cobrem. Na dúvida, não ajuste.
3. Achados julgados: problemas visíveis que nenhum script mede (conteúdo ou números inventados, botões e links sem destino, áreas vazias no lugar de conteúdo, gráficos sem valores, estados de vazio/erro/carregando ausentes, quebra de layout), cada um preso ao ID do componente ou da região, com 10 (leve), 20 (médio) ou 30 (grave) pontos e `vp` "desktop" ou "mobile".
4. `warns_descartados`: gates de WARN do `notas-mecanicas.json` que você verificou serem falsos alarmes.

Escreva exatamente dois arquivos e nada mais:
- `<O>/ajustes.json`: `{"eixos_hallmark": {"P":n,"H":n,"E":n,"S":n,"R":n}, "justificativa_eixos": {"P":"…",…}, "ajustes": {"<dimensão>": {"delta": n, "motivo": "…"}}, "warns_descartados": [], "notas_visuais": {}}`
- `<O>/julgados.json`: `[{"vp": "desktop", "componente": "C6", "problema": "…", "pontos": 20}, …]`

Não altere nenhum outro arquivo. Responda com um resumo de até 6 linhas.

Modo mobile (`checagens.json` tem `"modo": "mobile"`): a tela é de aplicativo e só existe a medição do celular. Além do que está acima, leia `<O>/shots/larg-*.png` (320, 360, 430 e paisagem), `<O>/estados/*.png` e `estados` em `<O>/checagens.json` (um estado por toque, rolagem até o fim e carrosséis no fim). Trate como achado julgado (com ID do componente, `vp` "mobile"): elemento coberto por outro, último item atrás de barra fixa, controle que não muda nada ao toque, folha ou diálogo sem como fechar, estado vazio ou de erro ausente, ação só por gesto, texto que não cabe em 320px, ação principal fora da zona do polegar (terço de cima da tela, longe do alcance de uma mão) ou colada a uma ação destrutiva. Ignore os gates de landing page (hero, CTA na dobra, largura máxima). Use os eixos P/H/E/S/R para app: H é a clareza de qual é a ação principal da tela e onde está a navegação.
