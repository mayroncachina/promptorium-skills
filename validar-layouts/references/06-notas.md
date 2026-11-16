# Notas

As 7 dimensões e os pesos (a soma dá 100):

| Dimensão | Peso | De onde vem |
| --- | --- | --- |
| Acessibilidade | 20 | Hallmark "Assets and access" + foco, contraste e movimento reduzido; checagens de alt, label, botão só-ícone, lang e títulos |
| Layout e responsividade | 15 | Hallmark "Structure and layout"; rolagem horizontal no mobile |
| Tipografia e cor | 15 | Hallmark "Colour and surface" e "Type"; texto < 12px |
| Hierarquia e clareza | 15 | 50% mecânica (gates 44b e 58; widgets diferentes entre telas) + 50% eixo H do Hallmark |
| Originalidade (anti-"cara de IA") | 15 | 50% mecânica (Hallmark "Chrome and copy", emoji) + 50% média dos eixos P, S e R |
| Interação e estados | 10 | Hallmark "Motion and interaction"; alvos de toque < 24px no mobile (mínimo WCAG 2.2) e entre 24 e 43px (abaixo dos 44px recomendados); botões de ação diferentes entre telas ([11-consistencia.md](11-consistencia.md)) |
| Conteúdo e completude | 10 | Gates de texto e métricas inventadas (19, 46a, 46b, 69); title, erros no console |

Desconto mecânico por gate distinto: FAIL −1,5 · REFLEX −0,75 · WARN confirmado −0,25, mais −0,1 por ocorrência extra (até −0,5). As "regras da casa" do Hallmark (54, 58, 63, 67), mais rígidas que o mercado, pesam como REFLEX. Achados Finish (F-checks) não descontam: viram sugestões.

1. Rode `python3 <SKILL>/scripts/notas.py "$O/sloplint.json" "$O/checagens.json" /tmp/vl-tools/hallmark/skills/hallmark/references/gates.md > "$O/notas-mecanicas.json"` (com `O=<TMP>/out/<S>`) e leia os motivos.
2. Escreva `$O/ajustes.json`. Se a ferramenta Agent existir, prefira que um **avaliador independente** escreva este arquivo e o `julgados.json` (instruções em `<SKILL>/scripts/avaliador.md`; modo correção em [09-modo-correcao.md](09-modo-correcao.md)): a nota não depende de quem fez a leitura, e no modo correção isso é obrigatório. Formato:
   ```json
   {"eixos_hallmark": {"P": 3, "H": 4, "E": 3, "S": 2, "R": 3},
    "justificativa_eixos": {"P": "...", "H": "...", "E": "...", "S": "...", "R": "..."},
    "ajustes": {"acessibilidade": {"delta": -1, "motivo": "ordem de foco quebra no menu mobile (visto no screenshot 375)"}},
    "warns_descartados": ["29"],
    "notas_visuais": {}}
   ```
   `delta` vai de −2 a +2 e **exige motivo concreto**, apontando algo que o script não mede. Na dúvida, não ajuste. Deixe `notas_visuais` vazio.
3. Rode de novo com o `ajustes.json` como 4º argumento → `$O/notas.json`. Essa é a nota que vai para o relatório. Status: ≥85 **Pronto para entregar** · 70–84 **Ajustes pontuais** · 50–69 **Revisão necessária** · <50 **Refazer**. Um FAIL de contraste, foco ou movimento reduzido impede "Pronto para entregar".

Nunca invente nota fora do script, nem arredonde para cima.


## Modo mobile

Quando `checagens.json` traz `"modo": "mobile"` (artboard de até 500px, ver [10-modo-mobile.md](10-modo-mobile.md)), o `notas.py` muda sozinho:

| Dimensão | Peso web | Peso mobile |
| --- | --- | --- |
| Acessibilidade | 20 | 20 |
| Layout e responsividade | 15 | 15 |
| Tipografia e cor | 15 | 10 |
| Hierarquia e clareza | 15 | 10 |
| Originalidade | 15 | 10 |
| Interação e estados | 10 | 25 |
| Conteúdo e completude | 10 | 10 |

Descontos extras no mobile: elemento coberto por outro −1,5 (até −3) · transbordo em 320/360/430/paisagem −1,5 cada (até −3; não vale para artboard de largura fixa) · barra de navegação com mais de 5 itens −1,5 · carrossel só por gesto −1 cada (até −2) · campo sem `inputmode`/`type` −0,5 cada (até −1,5) · texto de campo abaixo de 16px −0,5 cada (até −1,5) · alvos a menos de 8px um do outro −0,5 cada (até −2) · barra de navegação fora da altura usual −0,75 cada (até −1,5) · controle que não muda nada ao toque −0,5 cada (até −2) · alvos de toque abaixo de 44px −0,25 cada (até −1,5). Os gates de landing page do Hallmark (44b, 44c, 44d, 6a, 59, 71, 77, 78, 79) não contam. Para Flutter, Android e Material, rode com `VL_ALVO=48` (alvo mínimo de 48dp em vez de 44pt).
