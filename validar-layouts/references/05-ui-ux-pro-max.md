# Auditoria ui-ux-pro-max

```bash
U=/tmp/vl-tools/uupm/.claude/skills/ui-ux-pro-max
python3 $U/scripts/search.py "<consulta>" --domain <domínio> -n 3
```

1. Leia `$U/SKILL.md` (tabela de prioridades 1→10) e `$U/references/quick-reference.md`. Percorra as 10 categorias como checklist sobre os screenshots e o código, da prioridade 1 (Acessibilidade) à 10 (Gráficos).
2. Para **cada problema** encontrado (pelas checagens do `checagens.json`, do `componentes-<vp>.json` ou na sua leitura), busque a regra correspondente com uma consulta curta pelo resultado observável (ex.: `"touch target size" --domain ux`, `"form label error" --domain ux`, `"horizontal scroll mobile" --domain ux`). Cite no achado o "Do", o "Don't" e a severidade da regra, e use o "Code Example Good" como base da correção.
3. **Sistema de design recomendado**: identifique tipo de produto e setor a partir do conteúdo do layout e rode `search.py "<tipo> <setor> <palavras-chave>" --design-system -p "<nome>"`. Compare estilo, paleta e tipografia recomendados com os do layout. Trate como **referência**, não como verdade: só vira sugestão o que melhora o layout para o público dele.
4. Telas de app ou mobile: rode o Pre-Delivery Checklist de `$U/references/pro-rules.md`.



## No modo mobile

Em vez da leitura geral das 10 categorias, a régua principal é o **Pre-Delivery Checklist de app** (`$U/references/pro-rules.md`) e as categorias 1, 2, 5, 8 e 9 (acessibilidade, toque, layout, formulários, navegação). Consultas úteis: `"touch target size" --domain ux`, `"bottom nav limit" --domain ux`, `"gesture alternative" --domain ux`, `"safe area" --domain web`, `"input type keyboard" --domain ux`. Para Flutter ou Material, acrescente `--stack flutter` e use alvo de 48dp (`VL_ALVO=48`). O sistema de design recomendado entra só como referência. Detalhes em [10-modo-mobile.md](10-modo-mobile.md).
