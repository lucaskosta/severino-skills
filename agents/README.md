# Severino — Adaptações para outros agentes

O núcleo do Severino (schema SQL + motor Python) funciona com qualquer agente.
O que muda é o mecanismo de invocação.

---

## Cursor

**Formato:** `.cursor/rules/*.mdc` (Cursor 0.43+)

**Instalação:**
```bash
mkdir -p .cursor/rules
cp agents/cursor/*.mdc .cursor/rules/
```

Coloque na pasta do seu diretório de dados (`$SEVERINO_DATA_DIR`).
O Cursor ativa cada regra automaticamente quando detecta que a conversa
se encaixa na `description` do frontmatter.

Para invocar explicitamente, diga ao Cursor: _"use a regra severino-anota"_.

**Arquivos:**
- `severino-pergunta.mdc` — onboarding
- `severino-anota.mdc` — registro diário
- `severino-pente-fino.mdc` — fechamento do mês
- `severino-conselheiro.mdc` — diagnóstico e estratégia

---

## GitHub Copilot

**Formato:** `.github/copilot-instructions.md`

**Instalação:**
```bash
mkdir -p .github
cp agents/copilot/copilot-instructions.md .github/
```

Coloque no seu diretório de dados (`$SEVERINO_DATA_DIR`).
O Copilot lê este arquivo automaticamente em todas as conversas do repositório.

> **Limite:** Copilot tem contexto menor que Claude Code ou Cursor. As 4 skills
> estão condensadas em um único arquivo. Se o modelo parecer confuso, prefira
> o Cursor ou o system prompt genérico.

---

## Qualquer LLM (genérico)

**Formato:** system prompt — funciona com Claude API, OpenAI, Gemini, Mistral,
LM Studio, Ollama, etc.

**Uso:**
1. Abra `agents/generic/system-prompt.md`
2. Cole o conteúdo como **system prompt** na interface ou API que você usa
3. Nas mensagens do usuário, descreva o que quer fazer normalmente

**Via API (exemplo com curl):**
```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-opus-4-8",
    "max_tokens": 4096,
    "system": "'$(cat agents/generic/system-prompt.md)'",
    "messages": [{"role": "user", "content": "paguei o aluguel hoje 1200 reais"}]
  }'
```

---

## Comparativo

| | Claude Code | Cursor | Copilot | Genérico |
|---|---|---|---|---|
| Invocação | `/severino-anota` | Automática por contexto | Sempre ativo | System prompt |
| Progressive disclosure | ✅ (references/) | Parcial | ✗ | ✗ |
| Arquivos separados por skill | ✅ | ✅ | ✗ (1 arquivo) | ✗ (1 arquivo) |
| Melhor para | Dev / power user | Dev + IDE | IDE rápido | API / qualquer LLM |
