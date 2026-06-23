# Severino — Suíte de Skills Financeiras

> Plano para transformar o sistema financeiro atual num **conjunto de skills portável**, que possa ser entregue a outras pessoas.
> Produto batizado de **Severino** — uma persona com tom próprio (ver §2). Esse tom vale pra **tudo**: skills, markdowns, mensagens, docs.
> Status: **brainstorm aprovado** — nada implementado ainda. Decisões já travadas marcadas abaixo.

---

## 1. Conceito

Separar o **motor** (genérico, portável) dos **dados pessoais** (perfil de cada um). Hoje estão grudados.

O produto é: **pasta de skills + motor + templates**. Instala em qualquer pessoa rodando a skill de onboarding.

**Diferenciais vs apps de finanças:**
- **Entrada conversacional** — sem formulário, você fala e o Severino registra.
- **Contexto persistente** — o Severino lembra sua vida financeira inteira.
- **Educação + cobrança ativa** embutidas — não só registra, ensina e cobra.

A dor nº 1 que ataca: **alimentar o dado e manter contexto**. O truque é que tudo que se repete vira item do perfil, e o fechamento mensal vira um **checklist gerado**, não uma entrevista do zero.

---

## 2. Persona & Tom — Severino  ⭐ (vale pra TUDO)

**Quem é o Severino:** o personagem que cuida do teu dinheiro. Arquétipo do **zelador / contador antigo** — durão de fora, coração mole. Anota tudo no caderninho, sabe onde cada centavo foi parar, e não tem papas na língua: se tu gastou besteira, leva bronca; se segurou e sobrou, leva elogio e ainda sai com uma sugestão do que fazer. Está **sempre do teu lado** — a bronca é de quem se importa.

**Tom de voz (aplicar em skills, mds, mensagens, diagnósticos):**
- Fala de gente, direta, de quem tem estrada: *"ó"*, *"olha aqui"*, *"rapaz"*, *"vô te falar uma coisa"*, *"pois é"*.
- **Honesto, sem dourar a pílula.** Bronca quando merece, elogio quando merece.
- **Humor sutil, nunca palhaçada.** Sábio, não bobo.
- Firme, mas acolhedor. Nunca humilha — corrige.
- **Educação financeira na lata**, linguagem simples — explica como quem ensina pro neto.

> Diretriz de implementação: toda mensagem ao usuário e todo texto gerado (resumos, alertas, broncas, elogios) saem **na voz do Severino**. Os SPEC/HANDOFF dos repos devem repetir esta seção.

---

## 3. Base atual (ponto de partida)

| Peça | O que é |
|---|---|
| **DB SQLite** | Fonte da verdade. `Financeiro/finance-mcp-server/data/finance.db`. Tabelas: `transactions`, `budgets` (vazia), `goals` (vazia). |
| **Gerador** | `Financeiro/scripts/update_finance_graphs.py` → 12 SVGs. |
| **Markdown** | Camada de leitura humana. |
| **Skill `finance-sync`** | Registra delta + sincroniza md + regenera gráficos. (Vira o `severino-anota`.) |

### Fraqueza estrutural a corrigir
O gerador hoje **lê valores por regex dos markdowns** (CONVENCOES §9 — "marcadores obrigatórios"). Isso amarra tudo ao formato pessoal do mês (escola, jiu, imobiliária...). Para outra pessoa usar, ela teria que replicar os mesmos marcadores — **não escala**.

→ **Correção:** gráficos passam a ler de um `estado.json` derivado do DB. O markdown vira só leitura. Some o acoplamento por regex.

---

## 4. Decisões travadas

1. **Nome:** suíte = **Severino**; persona + tom de §2 valem em tudo.
2. **Nomes das skills (definitivos):** `severino-pergunta` · `severino-anota` · `severino-pente-fino` · `severino-conselheiro`.
3. **Gráficos DB-driven** — gerador lê de `estado.json` derivado do DB, não mais regex do markdown.
4. **Você primeiro, generaliza depois** — motor já desacoplado, mas validado rodando no sistema do Taru antes de abstrair categorias/regras.
5. **4 skills**, com `severino-anota` como motor compartilhado (não duplicar lógica de consolidação).
6. **3 repos** (ver §9): público (produto) + privado (teu dado) + cockpit (referencia o privado).

---

## 5. Arquitetura: 1 fundação + 4 skills

### Fundação (substrato, não é skill)

- **Perfil financeiro** = núcleo. Entradas, contas, cartões, dívidas, investimentos, gastos recorrentes, metas, tom do coach. Mora no **DB** (tabelas novas) + **`PERFIL.md`** legível.
- **Motor**: schema + gerador + templates, parametrizados (nada hardcoded).

**Pulo do gato:** tudo que repete vira **`recurring_item`** no perfil → vira o checklist do `severino-pente-fino`. Mata a dor de alimentar dado.

---

### Skill 1 — `severino-pergunta` — Abrir a Ficha (onboarding)

| | |
|---|---|
| **Objetivo** | O Severino te conhece: monta o dossiê financeiro do zero. |
| **Gatilho** | "começar do zero", "configurar minhas finanças", primeira vez. |
| **Como** | Entrevista por **blocos**, 1 de cada vez, confirma antes de seguir, aceita "não sei / depois". |
| **Blocos** | Entradas → Contas/bancos → Cartões → Dívidas/financiamentos → Investimentos → Gastos fixos recorrentes → **Metas** (juntar 5k viagem, reserva, investir...) → Perfil de risco + tom do coach. |
| **Grava** | DB (tabelas novas) + `PERFIL.md` + cria a árvore de pastas + popula `goals`. |
| **Encadeia** | Chama `severino-anota` → gera o 1º painel. |

### Skill 2 — `severino-anota` — O Motor (registra na hora) — evolução do `finance-sync`

| | |
|---|---|
| **Objetivo** | Pegar delta → gravar DB → derivar `estado.json` → gerar md + 12 gráficos. |
| **Gatilho** | Chamada por `pergunta`/`pente-fino` **+** ad-hoc "registra esse gasto" (papel atual do `finance-sync`). |
| **Modos** | (a) consolidação completa; (b) **captura rápida** no meio do mês ("gastei 50 no mercado"). |
| **Regra** | Aplica reserva automático em toda entrada (% configurável no perfil — não fixo em 10%). |

### Skill 3 — `severino-pente-fino` — Fecha o Mês (checklist)

| | |
|---|---|
| **Objetivo** | Alimentação recorrente sem dor — o ritual de fim de mês. |
| **Como** | Gera **checklist dos `recurring_items`** + faturas previstas. Pergunta item a item, na voz do Severino: *"Ó, o financiamento de R$X venceu dia 10 — pagou? [s/n/outro valor]"*, *"A diarista veio esse mês? Quantas vez?"*, *"Fatura do Nubank — fechou em quanto?"*. Captura entradas (salário caiu? bico?). |
| **Encadeia** | Joga tudo em `severino-anota` → novo painel + panorama do mês. |

### Skill 4 — `severino-conselheiro` — Diagnóstico + Estratégia + Bronca (a joia)

| | |
|---|---|
| **Objetivo** | Ler tudo, diagnosticar, traçar estratégia, monitorar, **dar bronca** ou sugerir alocação de sobra. |
| **Modo Diagnóstico** | Raio-x: endividamento, reserva, queima mensal, vazamentos (tipo "outros gastos" a rastrear). |
| **Modo Estratégia** | Define o plano: meta de reserva, método de quitação (avalanche/snowball), tetos por categoria (usa `budgets`), alocação da sobra → grava `ESTRATEGIA.md` + tabela `strategy`. |
| **Modo Acompanhamento** | Mês real × plano → **bronca** se estourou/não cumpriu; **elogio + sugestão** se sobrou (quita dívida X / reforça reserva / investe). |
| **Educação** | Explica o *porquê* no contexto (o que é reserva de emergência, avalanche vs snowball, custo de oportunidade de quitar vs investir). Tudo na voz do Severino. |

---

## 6. Flow de uso

### Ciclo de vida

```
1x, no começo      severino-pergunta      → monta tua ficha
no dia a dia       severino-anota         → captura gasto/entrada na hora
1x por mês         severino-pente-fino    → checklist dos recorrentes
quando quiser      severino-conselheiro   → diagnóstico + bronca + plano
```

O **motor (`severino-anota`)** é o eixo: as outras 3 chamam ele pra consolidar e redesenhar o painel.

### Por dentro de cada skill

**`severino-pergunta`** (1x)
```
Severino se apresenta → entrevista por blocos (confirma cada um, aceita "depois")
→ grava perfil no DB + PERFIL.md → define os recorrentes → chama o motor (1º painel)
→ "Pronto, rapaz. Tua vida tá no mapa."
```

**`severino-anota`** (toda hora)
```
"gastei 50 no mercado" → entende valor+categoria+data (pergunta só se ambíguo)
→ aplica reserva nas entradas → grava DB → deriva estado.json
→ atualiza mds + 12 gráficos → "Anotado. Caixa do mês: R$ X."
```
*(as outras skills chamam em modo silencioso pra consolidar.)*

**`severino-pente-fino`** (1x/mês)
```
lê perfil → monta lista de recorrentes + faturas → vai item a item:
   "Financiamento R$ X venceu dia 10 — pagou? [s/n/outro]"
→ captura entradas do mês + marca atrasados → chama o motor
→ panorama: entrou / saiu / sobrou → gancho: "Quer que eu analise o mês?"
```

**`severino-conselheiro`** (quando quiser)
```
lê DB + estado.json + estratégia anterior
→ DIAGNÓSTICO (dívida, reserva, queima, vazamentos)
→ ESTRATÉGIA (meta reserva, quitação, tetos, sobra) → grava ESTRATEGIA.md
→ BRONCA/ELOGIO (plano × real) → ensina o conceito
→ fecha com 1–3 ações pro próximo mês
```

### O loop do mês

```
   pergunta (1x)
       │
       ▼
   ┌──────────── mês a mês ────────────┐
   │                                    │
   anota ◄──── pente-fino               │
   (avulso)    (fim do mês)             │
       │            │                    │
       └─────┬──────┘                    │
             ▼                           │
        conselheiro ──► bronca/plano ────┘
                        (ajusta o próximo mês)
```

Tu alimenta o ano todo com **dois gestos**: `anota` no susto do dia a dia + `pente-fino` no fim do mês. O `conselheiro` fecha o ciclo cobrando o plano.

---

## 7. Modelo de dados

Manter `transactions`. Usar `budgets` + `goals` (hoje vazias). **Adicionar:**

`income_sources` · `accounts` · `cards` · `debts` · `investments` · `recurring_items` · `strategy`

Derivar **`estado.json`** do DB → o gerador lê dele (não mais regex do markdown).

---

## 8. Contratos entre as skills

```
pergunta    ──cria perfil──►  DB ──► anota ──► painel
pente-fino  ──checklist────►  DB ──► anota ──► painel
anota       ──deriva──────►  estado.json ──► gerador ──► 12 SVGs
conselheiro ──lê──────────►  DB + estado.json + ESTRATEGIA.md ──► bronca/sugestão
```

---

## 9. Os 3 repos (visão final)

```
1. severino (público)   = o produto: skills + motor. Genérico, sem teu dado. É o que tu compartilha.
2. financeiro (privado) = tua instância: teu dado (DB, mds, gráficos, PERFIL, ESTRATEGIA). "Executar tua gestão."
3. IA/assistente (cockpit) = fica como está; só referencia o #2 pra dinheiro.
```

**Sacada:** `#2 = #1 instalado + teu dado`. O repo pessoal **não tem código de produto** — tem só dado + config. As skills moram global em `~/.claude/skills/` e rodam contra o diretório de dado que tu apontar.

| Quando | Ação |
|---|---|
| **Agora** | Scaffolda o repo do produto (futuro público). Dev roda contra `IA/assistente/Financeiro/` como dado de teste. |
| **Fases 0–4** | Constrói/valida motor + 4 skills usando teu dado real, in loco. |
| **Quando estabilizar** | Extrai `IA/assistente/Financeiro/` → repo privado `financeiro`. Cockpit passa a referenciar ele. |

---

## 10. Ordem de construção

**Fase 0 — Refatorar o motor (base de tudo)**
- Gerador passa a ler `estado.json` derivado do DB (não mais marcadores de md).
- Migra os dados atuais para o DB completo (popular `recurring_items`, `goals`, dívidas a partir do que já existe nos mds).
- *Sem isso, as 4 skills não têm chão.* É o primeiro tijolo.

**Fase 1 — `severino-anota`** (evolui o `finance-sync`) — delta → DB → `estado.json` → md + 12 SVGs. Modo captura rápida. Validar no mês corrente.

**Fase 2 — `severino-pergunta`** — onboarding por blocos → perfil + DB + 1º painel.

**Fase 3 — `severino-pente-fino`** — checklist gerado dos `recurring_items`.

**Fase 4 — `severino-conselheiro`** — diagnóstico → estratégia → bronca + educação.

---

## 11. Próximo passo

Dar o sinal para scaffoldar o repo **`severino`** (+ SPEC + HANDOFF, já com a §2 do tom) e depois a **Fase 0**.
