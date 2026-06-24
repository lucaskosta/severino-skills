#!/usr/bin/env bash
# Severino — instalador
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

# 3. Verificar Python 3.10+
PYTHON=""
for py in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$py" &>/dev/null; then
    ver=$("$py" -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null)
    if [ "$ver" = "True" ]; then
      PYTHON="$py"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "❌  Python 3.10+ não encontrado."
  echo "    Instale via: brew install python@3.13"
  exit 1
fi
echo "✓  Python: $($PYTHON --version)"

# 4. Criar virtualenv e instalar dependências do MCP server
VENV_DIR="$REPO_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
  echo ""
  echo "Criando virtualenv em $VENV_DIR..."
  "$PYTHON" -m venv "$VENV_DIR"
fi

echo "Instalando dependências Python (mcp)..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt"
echo "✓  Dependências instaladas"

# 5. Criar diretório de skills se necessário
mkdir -p "$SKILLS_DIR"

# 6. Criar symlinks para cada skill
echo ""
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

# 7. Criar banco de dados se não existir
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
fi

# 8. Registrar MCP server no Claude Code
SETTINGS="$HOME/.claude/settings.json"

if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

"$VENV_DIR/bin/python3" - <<PYEOF
import json, pathlib, sys

settings_path = pathlib.Path('$SETTINGS')
cfg = json.loads(settings_path.read_text())
cfg.setdefault('mcpServers', {})['severino'] = {
    'command': '$VENV_DIR/bin/python3',
    'args': ['$REPO_DIR/engine/mcp_server.py'],
    'env': {
        'SEVERINO_HOME': '$REPO_DIR',
        'SEVERINO_DATA_DIR': '$SEVERINO_DATA_DIR',
    }
}
settings_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print('✓  MCP server registrado em $SETTINGS')
PYEOF

echo ""
echo "✅  Instalação concluída!"
echo ""
echo "Próximos passos:"
echo "  1. Reinicie o Claude Code para carregar o MCP server"
echo "  2. Abra uma conversa e digite: /severino-pergunta"
echo "  3. Siga o onboarding de 8 blocos"
echo ""
echo "Documentação: $REPO_DIR/README.md"
