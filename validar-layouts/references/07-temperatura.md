# Mapa de temperatura por componente

A temperatura mostra **onde** estão os problemas; a nota de [06-notas.md](06-notas.md) diz **quanto** o layout vale. As duas não se misturam: a temperatura não altera a nota.

1. Rode `python3 <SKILL>/scripts/temperatura.py "$O" "$O/notas.json"`. Cada componente recebe de 0° a 100° pela soma dos problemas medidos nele, uma vez por tipo: contraste 30 (+10 abaixo de 3:1), foco invisível 35, anel de foco fraco 25, só o foco padrão do navegador 12, alvo de toque < 24px 25 e de 24 a 43px 8, sem nome acessível 30, SVG sem aria-hidden 6, texto < 12px 12, `transition: all` 6, transbordo no celular 35. Os achados do Hallmark ligados ao componente (pela linha do código ou pelo texto) somam FAIL 15, REFLEX 8 e WARN 3 por gate, até 40; as regras da casa contam como REFLEX, e um gate já medido pelo Playwright no mesmo componente não conta de novo. A região fica tão quente quanto o seu pior ponto. Faixas: 0–19° frio · 20–39° morno · 40–59° atenção · 60–79° quente · 80–100° crítico.
2. **Achados julgados.** O que só a leitura vê (miniatura vazia, métrica inventada, botão sem destino, gráfico sem valores, tela que não decide para quem é) entra em `$O/julgados.json`, com o ID do componente tirado de `componentes-desktop.json` ou `componentes-mobile.json`:
   ```json
   [{"vp": "desktop", "componente": "C6", "problema": "miniatura vazia: nenhum projeto real", "pontos": 30}]
   ```
   Use 10 (leve), 20 (médio) ou 30 (grave), sempre com o problema escrito; inclua os achados da revisão de contexto limpo. Rode de novo com o arquivo como 3º argumento.
3. Abra `mapa-desktop-colunas.png` e `mapa-mobile-colunas.png` (Read) e confira: as caixas caem sobre os componentes certos? Os nomes fazem sentido? Se a detecção errou (um par de botões virou "card", uma região engoliu a página toda), diga isso no relatório, em vez de esconder.
4. `temperatura.json` traz, por largura, os itens em ordem de temperatura, com o resumo dos problemas já ordenado pelo peso. É de lá que saem a lista "componentes mais quentes" e os números do relatório.

O mapa usa uma escala de **um matiz só** (laranja, do claro ao escuro), porque mede intensidade; a página fica em cinza por baixo para que as cores dela não se confundam com a escala, e cada selo traz o número, então a cor nunca é a única informação.


