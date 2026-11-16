# Renderizar e checar (um artboard por vez)

```bash
python3 <SKILL>/scripts/dc_montar.py "<TMP>/project"            # modo automático
python3 <SKILL>/scripts/dc_montar.py "<TMP>/project" mobile      # ou desktop: força o modo de todos os artboards
```

A saída (também em `<TMP>/project/_vl_artboards.json`) lista cada artboard com título, tamanho, `pagina`, `interativo`, `celular` e **`modo`**. O modo é automático: artboard de até 500px de largura é **`mobile`** (tela de aplicativo); os demais são `desktop`. Quem chamou a skill pode forçar com a opção `mobile` ou `desktop` depois do link.

Para **cada artboard `<S>`** (o nome sem `.dc.html`), **um de cada vez** (a captura e o sloplint usam arquivos de trabalho na mesma pasta), rode a captura e, em seguida, o sloplint de [04-hallmark.md](04-hallmark.md), antes de passar ao próximo. O `captura.py` lê o modo do `_vl_artboards.json`:

```bash
python3 <SKILL>/scripts/captura.py "<TMP>/project/<S>.vl.html" "<TMP>/out/<S>"
```

- **Modo desktop**: `desktop-dobra.png` e `desktop-inteira.png` (1440×900), mais as de celular (390×844). Abra (Read) as dobras.
- **Modo mobile**: só o celular. Abra `mobile-dobra.png`, `mobile-inteira.png`, `shots/larg-*.png` (320, 360, 430 e paisagem) e `estados/*.png` (padrão, fim da rolagem, carrosséis, e um toque em cada controle). Detalhes em [10-modo-mobile.md](10-modo-mobile.md).
- Se `erros_console` em `checagens.json` tiver linhas `[dc-lite]`, ou a tela sair vazia ou quebrada, o runtime local não conseguiu desenhar alguma parte: diga isso no relatório e não penalize o layout por esse efeito. A renderização é local, não a do editor: diferenças finas são possíveis, e o relatório avisa isso numa linha.
- **Se `fidelidade` for `parcial`**, olhe a lista `bloqueados`: se o visual saiu quebrado por causa de algo bloqueado, diga isso no relatório e não penalize o layout pelo que é efeito do bloqueio. Imagens e fontes enviadas ao canvas não são baixadas ([01-baixar-canvas.md](01-baixar-canvas.md), passo 3): a área delas aparece vazia, e isso é "não verificado", não defeito.
- **Artboard interativo**: a auditoria vê o **estado padrão** (props com os valores padrão de `data-props`). No modo mobile a varredura de estados cobre os toques; no desktop, se o estado padrão já mostra um menu ou modal aberto, diga isso no relatório (um FAIL 73, "texto sob outro elemento", causado pelo fundo do modal vem desse estado).
