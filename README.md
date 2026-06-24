# Severino

> Seu zelador financeiro de bolso. Durão de fora, coração mole.

Severino é uma suíte de **4 skills para Claude Code** que transforma o Claude em um gestor financeiro pessoal com contexto persistente. Em vez de planilha ou formulário, você fala — o Severino anota, fecha o mês com você e te dá o diagnóstico com número real e razão citável.

---

## O que faz

| Skill | Quando usar |
|---|---|
| `/severino-pergunta` | Primeira vez: monta o dossiê completo (8 blocos) |
| `/severino-anota` | Dia a dia: "paguei aluguel", "recebi salário", "gastei 80 no mercado" |
| `/severino-pente-fino` | Fim do mês: checklist dos recorrentes, fecha o mês |
| `/severino-conselheiro` | Diagnóstico + estratégia + acompanhamento com números reais |

O conselheiro **não opina durante o onboarding**. Coleta fatos primeiro, estratégia no fim — baseada no seu perfil, suas dívidas, sua realidade.

---

## Requisitos

- [Claude Code](https://claude.ai/code) (CLI da Anthropic)
- Python 3.10+
- SQLite 3 (já vem no macOS/Linux)

> **Compatibilidade:** As skills funcionam exclusivamente com o **Claude Code**. O núcleo (schema SQL + motor Python) é portável para qualquer agente ou app.

---

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/lucaskosta/severino-skills.git
cd severino-skills
```

### 2. Definir variáveis de ambiente

Adicione ao seu `~/.zshrc` ou `~/.bashrc`:

```bash
export SEVERINO_HOME="$HOME/severino-skills"       # onde você clonou
export SEVERINO_DATA_DIR="$HOME/Financeiro"         # onde ficam seus dados (fora do git)
```

Recarregue:

```bash
source ~/.zshrc
```

### 3. Rodar o instalador

```bash
bash install.sh
```

O instalador:

- Cria symlinks das 4 skills em `~/.claude/skills/`
- Cria o banco de dados SQLite com o schema completo em `$SEVERINO_DATA_DIR/`
- Verifica que o Claude Code está instalado

### 4. Iniciar o onboarding

Abra uma conversa no Claude Code e digite:

```
/severino-pergunta
```

---

## Como funciona por dentro

```
Você fala  →  Skill (SKILL.md)  →  SQLite (finance.db)
                                        ↓
                               derive_estado.py
                                        ↓
                               estado.json  +  7 SVGs
                                        ↓
                            severino-conselheiro lê e fala
```

**Seus dados nunca saem do seu computador.** O banco SQLite fica em `$SEVERINO_DATA_DIR`, fora do repositório. Só o `estado.json` (um resumo derivado, sem dados brutos) é enviado ao Claude para análise.

### As 3 camadas do schema

| Camada | O que guarda |
|---|---|
| **Fatos** | perfil, categorias, contas, cartões, dívidas, investimentos, recorrentes, transações |
| **Objetivo** | metas (reserva, compra, quitar dívida, investir) |
| **Estratégia** | recomendação da IA gerada no fim — nunca na entrada |

### Diagnóstico baseado em indicadores citáveis

O conselheiro avalia 6 KPIs com thresholds de fontes reais:

| Indicador | Fonte |
|---|---|
| Comprometimento de renda | CFP Board |
| Taxa de poupança | Warren & Tyagi (2005) |
| Cobertura de reserva | CFPB (2023) |
| Debt-to-income (DTI) | FHA / BACEN |
| Peso de moradia | Harvard Housing Studies (2024) |
| Taxa máxima de dívida | BACEN Nota Crédito |

---

## Estrutura do repositório

```
severino-skills/
├── engine/
│   ├── schema.sql          # schema SQLite v2 + seed de categorias BR
│   ├── derive_estado.py    # DB → estado.json (+ diagnóstico + recomendação)
│   └── render_graphs.py    # estado.json → 7 SVGs
├── skills/
│   ├── shared/
│   │   ├── sql-examples.md       # INSERTs de referência (fonte única)
│   │   └── health-thresholds.md  # thresholds + referências citáveis
│   ├── severino-pergunta/
│   ├── severino-anota/
│   ├── severino-pente-fino/
│   └── severino-conselheiro/
├── modelagem/              # documentação das decisões de design (não vai pro DB)
├── install.sh              # instalador
└── README.md
```

---

## Privacidade

- Banco de dados: local, nunca sincronizado
- `*.db` e `data/` estão no `.gitignore`
- O Claude recebe apenas o `estado.json` (derivado, sem dados brutos)
- Sem conta, sem servidor, sem telemetria

---

## Contribuindo

Issues e PRs são bem-vindos. Antes de abrir um PR:

1. Teste o SQL novo contra o `engine/schema.sql` com `sqlite3`
2. Verifique que nenhum dado pessoal está em exemplos
3. Documente decisões de design em `modelagem/`

---

## Licença

MIT
