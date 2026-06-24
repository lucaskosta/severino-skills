#!/usr/bin/env bash
# Severino — instalador de skills
# Uso: bash install.sh

set -e

SKILLS_DIR="$HOME/.claude/skills"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Severino — instalador ==="
echo ""

# 1. Verificar Claude Code
if ! command -v claude &>/dev/null; then
  echo "❌  Claude Code não encontrado."
  echo "    Instale em: https://claude.ai/code"
  exit 1
fi

# 2. Verificar variáveis de ambiente
missing=0
if [ -z "$SEVERINO_HOME" ]; then
  echo "⚠️  SEVERINO_HOME não definido."
  missing=1
fi
if [ -z "$SEVERINO_DATA_DIR" ]; then
  echo "⚠️  SEVERINO_DATA_DIR não definido."
  missing=1
fi

if [ "$missing" -eq 1 ]; then
  echo ""
  echo "Adicione ao seu ~/.zshrc ou ~/.bashrc:"
  echo ""
  echo "  export SEVERINO_HOME=\"$REPO_DIR\""
  echo "  export SEVERINO_DATA_DIR=\"\$HOME/Financeiro\""
  echo ""
  echo "Depois rode: source ~/.zshrc && bash install.sh"
  exit 1
fi

# 3. Criar diretório de skills se necessário
mkdir -p "$SKILLS_DIR"

# 4. Criar symlinks para cada skill
for skill in severino-pergunta severino-anota severino-pente-fino severino-conselheiro; do
  target="$SKILLS_DIR/$skill"
  source="$REPO_DIR/skills/$skill"

  if [ -L "$target" ]; then
    echo "↺  $skill (já existe — atualizando)"
    rm "$target"
  elif [ -e "$target" ]; then
    echo "⚠️  $target já existe e não é symlink — pulando"
    continue
  fi

  ln -s "$source" "$target"
  echo "✓  $skill"
done

# 5. Criar banco de dados se não existir
DB_DIR="$SEVERINO_DATA_DIR/finance-mcp-server/data"
DB_PATH="$DB_DIR/finance.db"

if [ ! -f "$DB_PATH" ]; then
  echo ""
  echo "Criando banco de dados em $DB_PATH..."
  mkdir -p "$DB_DIR"
  sqlite3 "$DB_PATH" < "$REPO_DIR/engine/schema.sql"
  echo "✓  finance.db criado com schema v2"
else
  echo ""
  echo "ℹ️  Banco de dados já existe: $DB_PATH"
  echo "   Para aplicar o schema em um DB novo: sqlite3 finance.db < engine/schema.sql"
fi

echo ""
echo "✅  Instalação concluída!"
echo ""
echo "Próximos passos:"
echo "  1. Abra uma conversa no Claude Code"
echo "  2. Digite: /severino-pergunta"
echo "  3. Siga o onboarding de 8 blocos"
echo ""
echo "Documentação: $REPO_DIR/README.md"
