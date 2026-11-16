# Modo mobile (tela de aplicativo)

Liga **sozinho** quando o artboard tem até 500px de largura (`dc_montar.py` grava `"modo": "mobile"` no `_vl_artboards.json`). Para forçar: opção `mobile` ou `desktop` depois do link; `android`, `flutter` ou `app-android` usam alvo de toque de 48dp (`VL_ALVO=48`); sem isso, 44pt. Um canvas pode misturar os dois modos: cada artboard segue o seu.

## O que muda em relação ao modo desktop

| Etapa | Desktop | Mobile |
| --- | --- | --- |
| Capturas | 1440×900 e 390×844 | 390×844, 375, 360, 430, 320 e paisagem 844×390 |
| Estados | só o padrão | padrão, fim da rolagem, carrosséis no fim, um toque em cada controle (até 16) |
| Hallmark | gates de landing contam | sloplint com `--scope app`; gates de landing ignorados |
| Pesos | web | interação e estados 25; tipografia, hierarquia e originalidade 10 (ver [06-notas.md](06-notas.md)) |
| Temperatura | desktop e celular | só celular (o `ciclo.py` já usa o viewport que existe) |
| Foco por Tab | sim | não (toque, não teclado) |

## Checagens automáticas do modo mobile

- **Elemento coberto** (`mobile_estados.py`): o centro de cada controle visível é testado com `elementFromPoint`. Pega botão flutuante sobre a barra de navegação e último item atrás de barra fixa. Ignora o que está rolado para fora de uma área rolável e o que fica sob folha, diálogo ou cortina de tela inteira.
- **Controle sem efeito**: botão que, tocado, não muda a tela. Ignora o que já está selecionado (`aria-checked`, `aria-pressed`, `aria-selected`, `aria-current`).
- **Transbordo** em 320, 360, 430 e paisagem. **Não vale para artboard de largura fixa** (o `captura.py` detecta isso e marca `largura_fixa`): diga no relatório que 320 e 360 são "não verificados" e que o app real precisa ser responsivo.
- **Barra de navegação com mais de 5 itens**, **carrossel só por gesto** (sem botão no mesmo bloco) e **campo de texto sem `inputmode`/`type`** para e-mail, telefone, CPF, CEP, valor ou cartão (`componentes.py`).
- **Texto do campo com menos de 16px** (`campo_fonte`): no iOS o navegador dá zoom ao focar o campo e a tela "pula".
- **Alvos de toque a menos de 8px um do outro** (`alvo_junto`): vale para alvos pequenos; dois alvos grandes encostados (barra de abas, controle segmentado) não contam.
- **Altura das barras** (`barra_altura`): barra inferior fora de 49 a 96px (tab bar iOS 49pt, `NavigationBar` Material 80dp) e barra superior abaixo de 44px (iOS 44pt, app bar Material 56dp).
- Alvo de toque (24px mínimo WCAG 2.2; 44pt iOS; 48dp Material), contraste, texto abaixo de 12px, nome acessível e transbordo, como no desktop.

## O que o agente julga olhando as capturas (não há script)

Abra `estados/*.png` e `shots/larg-*.png` e procure: **zona do polegar**: a ação principal (o botão cheio mais importante da tela) está no terço de cima, longe do polegar, enquanto o resto da interação fica embaixo; ações frequentes só nos cantos superiores; ação destrutiva colada na principal · folha ou diálogo sem como fechar · estado vazio, de erro e de carregamento ausentes · ação principal da tela pouco visível ou escondida atrás de ícones pequenos · funções importantes só em botões pequenos · navegação que muda de lugar entre telas · rótulos da barra inferior cortados em 320 · conteúdo importante dentro da zona do gesto do sistema (rodapé) · teclado cobrindo o campo ou o botão de enviar · área de status e entalhe (não verificáveis no navegador: registre como "não verificado"). Cada achado leva o ID do componente e `vp` `mobile` no `julgados.json`.

## Para Flutter

O canvas é um desenho em HTML do app. Traduza os achados para o Flutter: alvo de 48dp (`MaterialTapTargetSize.padded`, `minimumSize`), `SafeArea`, `NavigationBar` com até 5 destinos, `TextInputType`/`autofillHints` nos campos, `Semantics` nos ícones, `MediaQuery.disableAnimations` para reduzir movimento e alternativa por botão para `PageView`/carrossel. Não invente comportamento que o desenho não mostra: vai para "pendente com você".
