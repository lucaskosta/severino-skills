---
name: severino-apresenta
description: 'Gera o relatório mensal consolidado em HTML — scores, KPIs, gráficos, calendário, tudo num único arquivo que abre direto no celular.'
argument-hint: 'Mês no formato YYYY-MM (ex: 2026-07). Sem argumento = mês atual.'
user-invocable: true
---

# severino-apresenta

Gera `RESUMO-YYYY-MM.html` — arquivo único, dark theme, mobile-friendly.  
Abre em qualquer navegador sem instalar nada.

---

## Passo 1 — Determinar o mês

Se o usuário passou argumento, usar esse mês. Senão, usar o mês atual (`date +%Y-%m`).

```bash
SLUG=$(python3 -c "
import sys
from datetime import datetime
ym = sys.argv[1]
months = {1:'janeiro',2:'fevereiro',3:'março',4:'abril',5:'maio',6:'junho',
          7:'julho',8:'agosto',9:'setembro',10:'outubro',11:'novembro',12:'dezembro'}
y,m = ym.split('-')
print(f'{months[int(m)]}-{y}')
" YYYY-MM)
```

---

## Passo 2 — Verificar pré-requisitos

Checar se `estado.json` já existe:

```bash
ls "$SEVERINO_DATA_DIR/meses/$SLUG/estado.json" 2>/dev/null
```

**Se não existir** → gerar estado + gráficos primeiro:

```bash
python3 "$SEVERINO_HOME/engine/derive_estado.py" YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
python3 "$SEVERINO_HOME/engine/render_graphs.py"  YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
```

**Se existir** → perguntar ao usuário:
> "Já existe `estado.json` para [mês]. Usar os dados existentes ou regenerar?"
- Regenerar → rodar os dois comandos acima
- Usar existente → continuar

---

## Passo 3 — Gerar o HTML

```bash
python3 "$SEVERINO_HOME/engine/generate_html.py" YYYY-MM --data-dir "$SEVERINO_DATA_DIR"
```

Saída esperada: `✓ /caminho/meses/SLUG/RESUMO-YYYY-MM.html`

---

## Passo 4 — Confirmar e abrir

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
| `estado.json não encontrado` | Mês sem dados ou onboarding não feito | Rodar `severino-pergunta` primeiro |
| `SVGs ausentes` | render_graphs não rodou | O HTML é gerado sem os gráficos — rode render_graphs e regenere |

---

## Conteúdo do relatório

O HTML inclui:

- **Cabeçalho**: mês, score `/100`, tier (verde/amarelo/laranja/vermelho)
- **Resumo**: renda confirmada · comprometido · sobra/déficit
- **6 KPIs de saúde**: barra de progresso com tier colorido
- **Recomendação**: foco principal · framework orçamentário · método de dívida · avalanche com data de quitação
- **Alertas**: flags vermelhos/laranjas/amarelos com ícones
- **Calendário**: vencimentos do mês com indicador pago/pendente
- **Reserva e patrimônio**: reserva atual vs meta · investimentos
- **7 gráficos inline**: entra×sai · 50/30/20 · categorias · saúde · calendário · cartões · dívidas
