#!/bin/bash
# Phase Validator for Ship Manager ADRs
# Usage:
#   phase-validator.sh context   - Output phase context for SessionStart
#   phase-validator.sh validate  - Output validation checklist for Stop hook

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../.phase-config.json"
ADR_DIR="$SCRIPT_DIR/.."

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Phase config not found at $CONFIG_FILE"
    exit 1
fi

# Get current phase
CURRENT_PHASE=$(jq -r '.currentPhase' "$CONFIG_FILE")
PHASE_NAME=$(jq -r ".phases[\"$CURRENT_PHASE\"].name" "$CONFIG_FILE")
PHASE_DESC=$(jq -r ".phases[\"$CURRENT_PHASE\"].description" "$CONFIG_FILE")

case "$1" in
    context)
        # Output context for SessionStart hook
        echo "═══════════════════════════════════════════════════════════════"
        echo "📋 CURRENT PHASE: $CURRENT_PHASE - $PHASE_NAME"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "📝 $PHASE_DESC"
        echo ""
        echo "📚 ADRs in scope for this phase:"

        # List ADRs with their titles
        jq -r ".phases[\"$CURRENT_PHASE\"].adrs[]" "$CONFIG_FILE" | while read -r adr_id; do
            # Determine directory based on prefix
            case "$adr_id" in
                FN-*) DIR="functional"; PREFIX="ADR-FN" ;;
                NF-*) DIR="non-functional"; PREFIX="ADR-NF" ;;
                UI-*) DIR="ui"; PREFIX="ADR-UI" ;;
            esac

            # Find the ADR file
            NUM=$(echo "$adr_id" | sed 's/[A-Z]*-//')
            # Use 10# to force decimal interpretation (avoid octal issues with 008, 009, etc.)
            PADDED_NUM=$(printf "%03d" "$((10#$NUM))")
            ADR_FILE=$(find "$ADR_DIR/$DIR" -name "${PREFIX}-${PADDED_NUM}-*.md" 2>/dev/null | head -1)

            if [ -f "$ADR_FILE" ]; then
                TITLE=$(head -1 "$ADR_FILE" | sed 's/^# //')
                echo "  • $adr_id: $TITLE"
            else
                echo "  • $adr_id: (file not found)"
            fi
        done

        echo ""
        echo "⚠️  When implementing, ensure compliance with these ADRs."
        echo "   Run validation before completing work."
        echo "═══════════════════════════════════════════════════════════════"
        ;;

    validate)
        # Output validation checklist for Stop hook
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "✅ PHASE $CURRENT_PHASE VALIDATION CHECKLIST"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""

        jq -r ".phases[\"$CURRENT_PHASE\"].validationChecklist[]" "$CONFIG_FILE" | while read -r item; do
            echo "  □ $item"
        done

        echo ""
        echo "───────────────────────────────────────────────────────────────"
        echo "Review the above checklist against your implementation."
        echo "To change phase: edit .phase-config.json and set 'currentPhase'"
        echo "═══════════════════════════════════════════════════════════════"
        ;;

    list)
        # List all phases grouped by major version
        echo "Available phases:"
        echo ""
        jq -r '.phases | to_entries | sort_by(.key) | .[] | "  \(.key): \(.value.name) (\(.value.adrs | length) ADRs)"' "$CONFIG_FILE"
        echo ""
        echo "Current phase: $CURRENT_PHASE ($PHASE_NAME)"
        echo ""
        echo "Use './phase-validator.sh set <phase>' to switch phases (e.g., 'set 1.2')"
        ;;

    set)
        # Set current phase
        if [ -z "$2" ]; then
            echo "Usage: phase-validator.sh set <phase_number>"
            exit 1
        fi

        # Validate phase exists
        if ! jq -e ".phases[\"$2\"]" "$CONFIG_FILE" > /dev/null 2>&1; then
            echo "Error: Phase $2 not found"
            exit 1
        fi

        # Update config (using temp file for portability)
        # Quote the phase value to handle "1.1" style phase IDs
        jq ".currentPhase = \"$2\"" "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
        NEW_NAME=$(jq -r ".phases[\"$2\"].name" "$CONFIG_FILE")
        echo "✓ Phase set to $2: $NEW_NAME"
        ;;

    *)
        echo "Phase Validator for Ship Manager ADRs"
        echo ""
        echo "Usage: phase-validator.sh <command>"
        echo ""
        echo "Commands:"
        echo "  context   - Output phase context (for SessionStart hook)"
        echo "  validate  - Output validation checklist (for Stop hook)"
        echo "  list      - List all available phases"
        echo "  set <n>   - Set current phase to n"
        ;;
esac
