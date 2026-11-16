# Preparar as ferramentas (uma vez por sessão)

Os **scripts** da skill ficam na pasta `scripts/` (não são copiados nem gravados em `/tmp`). O que fica em `/tmp/vl-tools/` são só as **ferramentas externas**: o Hallmark, o ui-ux-pro-max, Tailwind, puppeteer-core e um wrapper do Chrome.

```bash
bash <SKILL>/scripts/setup.sh
```

Anote a linha de versões que ele imprime (`hallmark <commit> | ui-ux-pro-max <commit>`): ela vai no rodapé do relatório. Se aparecer `FALTA: pip install playwright pillow`, instale (`pip install playwright pillow`). Sem o Chromium do Playwright, o `captura.py` usa o Google Chrome do sistema. Se `hallmark` ou `ui-ux-pro-max` aparecerem na lista de skills da sessão, carregue o SKILL.md delas com a ferramenta Skill para ter o contexto; os scripts sempre vêm da cópia clonada pelo `setup.sh`, para caminhos previsíveis.

## Mapa dos scripts (`<SKILL>/scripts/`)

| Arquivo | Para que serve |
| --- | --- |
| `setup.sh` | Clona e instala as ferramentas externas em `/tmp/vl-tools`. |
| `dc_lite.js` | Runtime local que faz o papel do `support.js` do Claude Design (`<helmet>`, `{{ }}`, eventos, `<sc-if>`, `<sc-for>`, `<dc-import>`, `Component extends DCLogic`). |
| `dc_montar.py` | Gera `<nome>.vl.html` ao lado de cada artboard, com as mesmas linhas do original, e decide o **modo** (mobile ou desktop). |
| `captura.py` | Screenshots, checagens do ui-ux-pro-max, snapshot para o sloplint e, no modo mobile, larguras extras e varredura de estados. |
| `componentes.py` | Divide a tela em regiões e componentes e mede cada um (contraste, foco por Tab, alvo de toque, nome acessível, transbordo, barra com mais de 5 itens, carrossel só por gesto, campo sem `inputmode`). |
| `mobile_estados.py` | Varredura de estados do modo mobile: toque em cada controle, fim da rolagem, carrosséis, elemento coberto, controle sem efeito. |
| `notas.py` | Nota mecânica por dimensão e nota final (pesos web ou mobile). |
| `temperatura.py` | Temperatura por componente e mapas desenhados. |
| `ciclo.py` | Controla o modo correção (avaliar, corrigir, reavaliar). |
| `avaliador.md` | Instruções do avaliador independente. |

Tudo roda com `python3` e usa o Playwright em Python. Se a rede bloquear CDNs, o `captura.py` serve o mesmo conteúdo a partir do npm.
