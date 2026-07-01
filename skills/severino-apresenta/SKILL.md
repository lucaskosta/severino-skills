---
name: severino-apresenta
description: 'Gera o relatório mensal consolidado em HTML — análise em linguagem natural, KPIs, posição consolidada, calendário completo (entradas + saídas) e gráficos, num único arquivo que abre no celular.'
argument-hint: 'Mês no formato YYYY-MM (ex: 2026-07). Sem argumento = mês atual.'
user-invocable: true
---

# severino-apresenta

Gera `RESUMO-YYYY-MM.html` — arquivo único, dark theme, mobile-friendly.  
Abre em qualquer navegador sem instalar nada.

---

## Passo 1 — Determinar o mês

Se o usuário passou argumento, usar esse mês. Senão, usar o mês atual.

```python
python3 -c "
from datetime import datetime; print(datetime.now().strftime('%Y-%m'))
"
```

Calcular o SLUG:

```python
python3 -c "
months = {1:'janeiro',2:'fevereiro',3:'março',4:'abril',5:'maio',6:'junho',
          7:'julho',8:'agosto',9:'setembro',10:'outubro',11:'novembro',12:'dezembro'}
ym = 'YYYY-MM'
y,m = ym.split('-')
print(f'{months[int(m)]}-{y}')
"
```

---

## Passo 2 — Gerar estado.json + gráficos

Checar se `estado.json` já existe:

```bash
ls "$SEVERINO_DATA_DIR/meses/SLUG/estado.json" 2>/dev/null
```

**Se não existir** → gerar:

```bash
python3 "$SEVERINO_HOME/engine/derive_estado.py"  YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
python3 "$SEVERINO_HOME/engine/render_graphs.py"   YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
```

**Se existir** → perguntar:
> "Já existe `estado.json` para [mês]. Usar os dados existentes ou regenerar?"
- Regenerar → rodar os dois comandos acima
- Usar existente → continuar

---

## Passo 3 — Gerar HTML preliminar (sem análise)

```bash
python3 "$SEVERINO_HOME/engine/generate_html.py" YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
```

---

## Passo 4 — Escrever análise em linguagem natural

Ler o `estado.json` do mês:

```bash
cat "$SEVERINO_DATA_DIR/meses/SLUG/estado.json"
```

Com base nos dados, escrever **dois parágrafos curtos**:

### `diagnosis_text` — "O que o Severino viu"
- Tom direto, sem amenizar
- Citar os números reais (score, percentuais, valores)
- Mencionar o que está bem E o que está crítico
- Máximo 4 frases

### `advice_text` — "O que fazer agora"
- 3 ações concretas com valores e datas
- Baseado em `recommendation` (foco, método, pay-yourself-first)
- Tom de conselheiro, não de relatório
- Máximo 4 frases

Salvar como JSON:

```bash
cat > "$SEVERINO_DATA_DIR/meses/SLUG/analysis.json" << 'EOF'
{
  "diagnosis_text": "...",
  "advice_text": "..."
}
EOF
```

---

## Passo 5 — Regenerar HTML com análise embutida

```bash
python3 "$SEVERINO_HOME/engine/generate_html.py" YYYY-MM \
  --data-dir "$SEVERINO_DATA_DIR" \
  --analysis-json "$SEVERINO_DATA_DIR/meses/SLUG/analysis.json"
```

---

## Passo 6 — Confirmar e abrir

Mostrar ao usuário:

> "Relatório gerado:  
> `[caminho completo do HTML]`
>
> Para abrir:
> ```bash
> open "$SEVERINO_DATA_DIR/meses/SLUG/RESUMO-YYYY-MM.html"
> ```"

Perguntar se quer abrir agora. Se sim, executar o `open`.

---

## Erros comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `$SEVERINO_HOME não definido` | Variável de ambiente ausente | `export SEVERINO_HOME=/caminho/para/severino` |
| `$SEVERINO_DATA_DIR não definido` | Variável de ambiente ausente | `export SEVERINO_DATA_DIR=/caminho/para/dados` |
| `estado.json não encontrado` | Mês sem dados | Rodar `severino-pergunta` primeiro |
| SVGs ausentes | render_graphs não rodou | HTML gerado sem gráficos; rodar render_graphs e regenerar |

---

## Conteúdo do relatório

O HTML inclui em ordem:

1. **Cabeçalho** — mês, score `/100`, tier colorido
2. **Análise em linguagem natural** — "O que vi" + "O que fazer"
3. **Resumo** — 3 cards: renda / comprometido / sobra–déficit
4. **Posição consolidada** — fluxo de caixa: entradas / comprometido / saldo projetado
5. **6 KPIs de saúde** — barras com tier colorido
6. **Recomendação** — foco · framework · avalanche com data de quitação · alertas
7. **Reserva e patrimônio** — reserva atual vs meta · investimentos
8. **Calendário** — todas as entradas (↑) e saídas (↓) do mês com indicador pago/pendente
9. **7 gráficos** — SVGs inline: entra×sai · 50/30/20 · categorias · saúde · calendário · cartões · dívidas
