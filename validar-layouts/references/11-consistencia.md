# Consistência entre telas

Widget que faz o mesmo papel tem de ter a mesma cara em todas as telas. **Botões de ação** são sempre do mesmo tipo (cheio, tonal, contorno ou texto), altura, forma (raio) e tamanho de texto, **salvo exceção informada**. Roda em todos os modos, sempre, e vale para o conjunto de artboards do canvas e para os widgets dentro de uma tela só.

## Como roda

1. O `captura.py` grava `inventario.json` (e recortes em `widgets/`) em cada artboard: botões de ação, botões de ícone, campos, cartões, atalhos em bloco, seletores (chips/abas), interruptores, cabeçalho e barra de navegação. Mobile mede em 390px, desktop em 1440px; só se compara widget medido no mesmo modo.
2. **Depois de capturar todos os artboards**, rode:

```bash
python3 <SKILL>/scripts/consistencia.py --todos "<TMP>/out" [--exceto "Excluir,cartao"]
```

Grava `consistencia.json` em cada artboard (problemas dele, exceções declaradas, referência por tipo) e `consistencia-acoes.png`, o painel dos botões lado a lado (precisa de Pillow; sem ele, só o JSON). Rode **antes** do `notas.py`: ele lê o arquivo sozinho.

3. Abra `consistencia-acoes.png` (Read) e confira no olho. O script mede tipo, altura, forma, texto e largura; **não pega** widgets de tipos diferentes para a mesma função (ex.: escolha de valor por chips numa tela e por lista noutra, ou ícone de outro conjunto). Isso é julgamento seu: registre em `julgados.json` com o ID do componente.

## Regra de comparação

- A referência de cada campo é o valor **mais usado no conjunto**; quem foge é alertado (tolerância: 2px em altura, largura e raio; 1px em fonte; pílula só iguala pílula).
- Botão de ação é agrupado pelo tipo, que vem do visual: **cheio** (fundo com contraste ≥ 2,2:1 com o entorno), **tonal** (fundo suave), **contorno** (só borda), **texto**. Dentro do tipo: altura, forma, fonte, peso e largura (cheia × ajustada).
- **Mesmo rótulo, tipo diferente** (ex.: "Salvar" cheio numa tela e contorno noutra) é alerta alto.
- Gravidade: tipo, altura e forma de botão de ação = **alta**; o resto = média.
- Cor não entra: botão destrutivo vermelho tem de ter o mesmo tamanho e forma, não a mesma cor.

## Exceções (só o que foi informado)

- Na chamada: `exceto=Excluir,cartao` (rótulo, parte do rótulo ou tipo: `acao`, `icone`, `campo`, `cartao`, `atalho`, `seletor`, `interruptor`, `cabecalho`, `navegacao`).
- No desenho: `data-vl-variante="motivo"` no elemento ou num pai. Aparece em `declarados`; liste no relatório e **não penalize**.
- Nunca crie exceção por conta própria. Se uma diferença parecer proposital (cartão de destaque, botão perigoso), alerte e pergunte no relatório se é intencional.

## Nota e relatório

`notas.py` desconta de **Interação e estados** (botão de ação: 0,5 por alerta, até 2,5) e de **Hierarquia** (demais widgets: 0,4 por alerta, até 2). O relatório traz uma seção "Consistência entre telas": tabela de referência por tipo (de `resumo`), alertas por artboard com `Arquivo.dc.html:linha`, o que difere e o valor de referência, o painel de botões e as exceções usadas.

## Para Flutter

Corrija na raiz: um único estilo por tipo (`FilledButton`, `FilledButton.tonal`, `OutlinedButton`, `TextButton`) com `ButtonStyle` no `ThemeData` (altura mínima, `shape`, `textStyle`), em vez de estilo em cada tela.
