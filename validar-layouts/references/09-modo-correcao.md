# Modo correção (só com `corrigir` na chamada)

Use quando a chamada trouxer `corrigir`. A **nota-meta** vem da chamada (padrão 80) e a **profundidade** também: `polish` (só o que um gate aponta: contraste, foco, estados, movimento) ou `restyle` (também o sistema visual: cores, tipografia, raios, sombras, controles), sempre **mantendo a estrutura e o conteúdo**; sem profundidade na chamada, use `polish`. `full` (recompor a página) fica fora do ciclo: recomende no relatório.

**Regras que o ciclo nunca quebra**
- O canvas auditado nunca é alterado. Cada rodada é uma pasta `vN/` dentro de `<TMP>/ciclo/<S>/`. A entrega final vai para `<PASTA>/<slug-do-canvas>-corrigido/` (os `.dc.html` da versão final aceita e o `canvas.json`, sem arquivos `_vl_*`, `*.vl.html` nem `entrada.txt`). Não publique no canvas; ofereça em uma linha publicar num canvas novo, se o usuário quiser.
- Edite os `.dc.html` respeitando o formato: buraco `{{ }}` é só caminho (nada de expressão), CSS de classes e `@media` no `<helmet>`, cores fixas escritas direto, `data-props` e a classe `Component` preservados (mexa na lógica só para acessibilidade, como `aria-expanded`).
- Não remover conteúdo; não reescrever textos; não inventar números, logos, depoimentos, nomes, destinos de link nem lógica (abas que trocam dados, envio de formulário). Isso vai para **"pendente com você"**. Exceções permitidas: nome acessível tirado do que já está na tela (aria-label de gráfico com os próprios dados) e aspas tipográficas.
- Decoração pode sair no restyle (brilho, vidro, ícones flutuantes, gradiente roxo-azul); o que carrega informação, não.
- A nota julgada de **toda** versão, inclusive a v0, vem do avaliador independente. Você corrige, ele avalia; nunca passe a ele o histórico nem o que mudou.

**Passo a passo** (por artboard; artboards diferentes podem andar em paralelo, cada um na sua pasta de ciclo)
1. `python3 <SKILL>/scripts/ciclo.py iniciar "<TMP>/ciclo/<S>" "<TMP>/project/<S>.dc.html"` cria `v0/` com a pasta do canvas (os artboards irmãos vão junto, para os `<dc-import>`).
2. `python3 <SKILL>/scripts/ciclo.py avaliar "<TMP>/ciclo/<S>/vN" [--scope app]`: monta o artboard com o runtime local, captura, Hallmark, checagens, notas e temperatura mecânicos.
3. Avaliador independente (Agent, em segundo plano): *"Leia <SKILL>/scripts/avaliador.md e siga-o à risca, com <O> = <TMP>/ciclo/<S>/vN/_vl_out e <HTML> = <TMP>/ciclo/<S>/vN/<S>.dc.html."* Enquanto ele roda, prepare a rodada de outro artboard.
4. `python3 <SKILL>/scripts/ciclo.py fechar "<TMP>/ciclo/<S>/vN" --meta 80`: nota final, temperatura, `historico.json`, `diff-v0.patch` e a **decisão**.
5. Decisão `continuar`: `python3 <SKILL>/scripts/ciclo.py nova "<TMP>/ciclo/<S>"` cria `v(N+1)` a partir da última versão aceita; corrija o `<S>.dc.html` dela e volte ao passo 2. Qualquer outra decisão encerra o ciclo.

**O que corrigir em cada rodada**, nesta ordem: (1) críticos: contraste, foco, movimento reduzido, rolagem lateral; (2) FAILs do Hallmark e problemas dos componentes mais quentes do mapa; (3) REFLEX e achados julgados que o restyle resolve (falsa indicação de clique, decoração, alturas de controle, hierarquia tipográfica, navegação que some no celular); (4) no restyle, o sistema: paleta própria (fuja da paleta padrão do framework), fonte de display com personalidade, títulos numa cor só. Calcule cada contraste novo antes de aplicar.

**Modo mobile no ciclo.** `ciclo.py` escolhe o modo pelo artboard (mobile até 500px) e a temperatura de parada vem do celular; para forçar, use `--modo mobile` ou `--modo desktop`. Corrija nesta ordem extra: elemento coberto, alvo de toque, ação só por gesto, campo sem `inputmode`. Veja [10-modo-mobile.md](10-modo-mobile.md).

**Critérios de parada** (no `ciclo.py`): meta atingida sem gate crítico (40, 41, 26a, 27, 34) · 3 rodadas de correção · ganho menor que 3 pontos · **regressão**: a nota geral cai, aparece crítico novo ou cai mais de 1 ponto a parte **mecânica** de uma dimensão (a versão é marcada `revertida` e o ciclo segue da anterior). Queda só na parte julgada vira **alerta** no relatório e não reverte: avaliações independentes variam de uma rodada para outra.

**Antes de corrigir um crítico, confirme que ele é real.** Se o Hallmark acusa algo que a página viva não mostra (por exemplo, transbordo que não aparece em `checagens.json` nem nos componentes), suspeite da medição e investigue antes de mexer no layout.

**Entrega**: relatório de antes e depois (o arquivo em `<PASTA>` e o canvas novo, [08-relatorio.md](08-relatorio.md)) com a tabela de rodadas (nota geral, 7 dimensões, críticos, temperatura máxima, decisão e alertas), telas antes e depois no desktop e no celular, mapas de temperatura antes e depois, mudanças por rodada, linhas alteradas (`diff-v0.patch`) e a lista **pendente com você** (achados julgados da versão final). Se a meta não foi atingida, diga por quê, em uma frase. Copie os artboards corrigidos para `<PASTA>` **antes** de apagar a pasta temporária (seção 9).



## Consistência no ciclo

Cada rodada compara o artboard com os **outros** do canvas: `python3 <SKILL>/scripts/ciclo.py avaliar <vN> --contra <pasta com os inventario.json dos demais>` (copie o `inventario.json` de cada um para a pasta, um por arquivo, nomeado com o artboard) e `--exceto "a,b"` para as exceções informadas. Sem `--contra`, só compara widgets dentro da própria tela. Corrija trocando para o padrão do conjunto, nunca mudando só a tela que estava certa. Ver [11-consistencia.md](11-consistencia.md).
