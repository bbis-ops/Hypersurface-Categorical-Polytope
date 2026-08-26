# Enter an API key for the loop-closure experiment without echoing it.
#
# MUST be sourced, not executed - an `export` in a child process cannot reach
# your shell:
#
#     source scripts/set_api_key.sh                  # OPENROUTER_API_KEY
#     source scripts/set_api_key.sh OPENAI_API_KEY   # or another variable
#
# The key is never printed and never passed as an argument (which would put it
# in your shell history). Verification is delegated to `--check` so this script
# and the experiment agree on which endpoint and model are used.

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "This script must be sourced so the export survives:"
    echo "  source scripts/set_api_key.sh"
    exit 1
fi

_cp_setkey() {
    local name="${1:-OPENROUTER_API_KEY}"
    local repo key tail

    case "$name" in
        OPENROUTER_API_KEY | OPENAI_API_KEY | LOOP_API_KEY) ;;
        *)
            echo "Unsupported variable: $name" >&2
            echo "Use OPENROUTER_API_KEY, OPENAI_API_KEY, or LOOP_API_KEY." >&2
            return 1
            ;;
    esac

    repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    echo
    echo "Paste your key for $name. Input is hidden."
    if [ "$name" = "OPENROUTER_API_KEY" ]; then
        echo "Get one at https://openrouter.ai/keys  (format: sk-or-v1-...)"
    fi
    printf 'Key: '
    read -rs key
    printf '\n'

    key="$(printf '%s' "$key" | tr -d '[:space:]')"
    if [ -z "$key" ]; then
        echo "No key entered; nothing changed."
        return 1
    fi
    if [ "$name" = "OPENROUTER_API_KEY" ] && [ "${key#sk-or-}" = "$key" ]; then
        echo "Note: OpenRouter keys normally start with 'sk-or-v1-'. Continuing."
    fi

    export "$name=$key"
    tail="${key: -4}"
    echo
    echo "Exported $name for this shell (ends ...$tail, ${#key} chars)."
    echo "This shell only - it is gone when you close the terminal."
    unset key

    echo
    echo "Verifying (one round-trip)..."
    if python "$repo/experiments/run_loop_closure.py" --check; then
        echo
        echo "Ready. Run the experiment with:"
        echo "  python experiments/run_loop_closure.py --api"
    else
        echo
        echo "Key is set but the check failed - see the message above."
        echo "Common causes: typo in the key, no quota, or the free window closed."
        return 1
    fi
}

_cp_setkey "$@"
