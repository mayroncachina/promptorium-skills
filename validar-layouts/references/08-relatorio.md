# Achados, o que falta e sugestões

**Gravidade** (use em todo o relatório):
- **Crítico**: FAIL do Hallmark ligado a acessibilidade, honestidade ou layout quebrado (contraste, foco, rolagem horizontal, métrica ou depoimento inventado); severidade High/Critical do ui-ux-pro-max nas prioridades 1 e 2.
- **Alto**: demais FAILs; REFLEX; severidade High do ui-ux-pro-max.
- **Médio**: WARN confirmado; severidade Medium; problemas julgados com impacto visível.
- **Baixo**: Finish (F-checks), severidade Low, refinamentos.

Cada achado tem: título curto · onde (`arquivo:linha`, seletor CSS ou ID do componente no mapa, e em qual largura) · evidência (o que se vê ou o trecho de código) · correção (o que fazer, com trecho de código quando ajudar) · fonte (`Hallmark 26a` ou `ui-ux-pro-max · Accessibility · Focus States`). Agrupe ocorrências repetidas do mesmo gate em um achado só, com a contagem.

**O que falta**: checklist marcado (✓/✗/n.a.) por artboard, cobrindo pelo menos: estados de foco · estados de hover/ativo · estados vazio, carregando e erro (quando há dados ou formulário) · validação e mensagens de erro em formulários · versão mobile sem rolagem horizontal · navegação e rodapé · `<title>` e `lang` (meta description e favicon são do editor: n.a.) · textos alternativos · respeito a movimento reduzido · contraste AA · telas da jornada que o layout pressupõe mas não existem (ex.: tem botão "Entrar" e não tem tela de login). Itens "n.a." precisam fazer sentido para o tipo de tela.

**Sugestões de melhoria**: no máximo 5 por artboard, ordenadas por ganho, separando **ganhos rápidos** (menos de 15 minutos) de **mudanças de direção**. Pelo menos uma deve vir do Hallmark (o que tornaria o layout específico deste produto, eixos S e P) e uma do sistema de design do ui-ux-pro-max, quando for relevante. Comece pelos componentes mais quentes do mapa.

Não invente: se algo não pôde ser verificado (parte que o runtime local não desenhou, imagem ou fonte enviada ao canvas), escreva "não verificado" e o motivo.


---

# Relatório: arquivo na pasta atual e canvas no Claude Design

Os dois têm o mesmo conteúdo.

**Arquivo na pasta atual (sempre).** Uma página HTML única e autossuficiente (CSS no próprio arquivo, imagens embutidas em base64, reduzidas para no máximo 2400 px de largura e em JPEG quando forem fotos de tela) gravada em `<PASTA>/relatorio-validacao-<slug-do-título-do-canvas>-<aaaa-mm-dd>.html`. Se já existir um arquivo com esse nome, acrescente `-2`, `-3`… em vez de sobrescrever. Abra a página com Playwright e veja a captura antes de seguir. Se esta sessão rodar na nuvem (a pasta atual não é do computador do usuário), envie também o arquivo com SendUserFile.

**Canvas no Claude Design (quando o tipo Design estiver disponível).** Liste os tipos de artifact (`list_types`) e use o tipo **Design**. Crie **um canvas novo** (nunca escreva no canvas auditado) com título `Validação — <título do canvas auditado> — <dd/mm/aaaa>` e siga à risca as instruções que o tipo devolver ao ser criado (formato `.dc.html`, `canvas.json`, um arquivo por envio, imagens só via upload, sem rede além do Google Fonts, sem verificação depois de publicar). Se houver um design system marcado como padrão, ele vale para o relatório também. Antes de escrever os artboards, **envie as imagens** (dobra desktop e mobile de cada artboard auditado e os dois mapas de temperatura) com `upload_asset` e use as URLs `/_blob/...` devolvidas. Sem o tipo Design, fique só com o arquivo e diga isso em uma linha.

Conteúdo (no canvas, um artboard PAGE de largura 1440 com `expand: "fill"` por item; no arquivo, uma seção por item):
1. **Resumo**: link e título do canvas auditado; nota geral do conjunto (média dos artboards) bem grande, com o status; data; quantos artboards; uma tabela de artboards × 7 dimensões com a nota geral de cada; os 5 problemas mais graves do conjunto; os ganhos rápidos; uma legenda curta de como a nota é calculada (pesos e descontos).
2. **Um bloco por artboard** (`A01-<slug>`, `A02-…`): miniaturas desktop e mobile; nota geral e status; as 7 notas como barras com o motivo principal de cada; os eixos P/H/E/S/R do Hallmark com a justificativa; achados agrupados por gravidade (onde = `Arquivo.dc.html:linha`); "O que falta" em checklist; sugestões (rápidas × de direção); profundidade Hallmark recomendada; sistema de design recomendado pelo ui-ux-pro-max lado a lado com o atual (paleta e fontes).
3. **Um bloco de mapa por artboard**: `mapa-desktop-colunas.png` e `mapa-mobile-colunas.png`, a legenda das cinco faixas e a lista dos 7 componentes mais quentes (temperatura, ID, nome e os 2 problemas de maior peso), com uma linha sobre as regiões mais quentes e o resumo do foco por Tab.
4. Com 2 ou mais artboards, **Comparativo**: ranking e o que cada um faz melhor que os outros.
5. Rodapé: versões (commits) do Hallmark e do ui-ux-pro-max; versão do canvas auditado (do `get_artifact`); "renderização local dos artboards, não a do editor"; arquivos que não puderam ser baixados (imagens e fontes enviadas); fidelidade do render; uma linha dizendo que a temperatura mostra onde estão os problemas e não entra na nota.

Visual do relatório: sóbrio e legível, cores de gravidade que também diferem em luminosidade (não só no tom), números alinhados à direita, contraste AA. O próprio relatório deve passar nos critérios que ele cobra: sem emoji como ícone, sem gradiente roxo-azul, sem rótulos em caixa alta espaçada.

---

# Conferir, entregar e apagar a pasta temporária

Antes de responder, confira: cada nota do relatório bate com o `notas.json` do artboard; cada temperatura bate com o `temperatura.json`; cada item de "O que falta" foi checado no código (ex.: `grep prefers-reduced-motion` antes de marcar movimento reduzido como ausente); todo contraste citado numa correção foi calculado; cada achado Crítico tem onde e evidência; o canvas auditado não foi alterado; o arquivo do relatório existe em `<PASTA>` e abre.

Então **apague a pasta temporária**, só depois de o relatório (e, no modo correção, os artboards corrigidos) estarem em `<PASTA>`:

```bash
rm -rf "<TMP>" && test ! -e "<TMP>" && echo "pasta temporária apagada"
```

Apague também se o trabalho parar no meio (erro, link recusado depois do download, pedido do usuário para cancelar). `/tmp/vl-tools` fica: são só as ferramentas, reaproveitadas na próxima vez, sem nenhum conteúdo do canvas.

Depois responda curto: nota geral, o pior problema, o componente mais quente, onde ficou o arquivo do relatório (nome do arquivo na pasta atual) e o canvas do relatório (o cartão do artifact já mostra o link). Se o usuário pedir PDF, gere-o a partir do mesmo HTML com Playwright (`page.pdf`, A4 paisagem), grave-o em `<PASTA>` e confira cada página rasterizada antes de entregar.

