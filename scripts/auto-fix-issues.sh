#!/bin/bash
# auto-fix-issues.sh - Automatically handle GitHub issues with Claude
#
# This script:
# 1. Checks for new open issues
# 2. Launches Claude to analyze and fix them
# 3. Claude will respond to issues, ask for clarification if needed, or fix and close
#
# Usage:
#   ./auto-fix-issues.sh              # Process all open issues
#   ./auto-fix-issues.sh --issue 5    # Process specific issue
#   ./auto-fix-issues.sh --dry-run    # Just show what would be processed
#
# Cron (check every 30 min):
#   */30 * * * * cd /path/to/library-manager && ./scripts/auto-fix-issues.sh >> /var/log/issue-bot.log 2>&1

set -e

REPO="deucebucket/library-manager"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PROMPT_FILE="$SCRIPT_DIR/issue-bot-prompt.md"
STATE_FILE="/tmp/library-manager-processed-issues.txt"
LOCK_FILE="/tmp/library-manager-issue-bot.lock"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check for lock file (prevent multiple instances)
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        log "Another instance is running (PID: $PID). Exiting."
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi

# Create lock file
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# Parse arguments
DRY_RUN=false
SPECIFIC_ISSUE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --issue)
            SPECIFIC_ISSUE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Make sure we're in the project directory
cd "$PROJECT_DIR"

# Check dependencies
for cmd in gh claude jq; do
    if ! command -v $cmd &> /dev/null; then
        log "Error: $cmd is not installed"
        exit 1
    fi
done

# Get open issues
log "Checking for open issues on $REPO..."

if [ -n "$SPECIFIC_ISSUE" ]; then
    ISSUE_DATA=$(gh issue view "$SPECIFIC_ISSUE" --repo "$REPO" --json number,title,body,comments 2>/dev/null || echo "")
    if [ -z "$ISSUE_DATA" ]; then
        log "Issue #$SPECIFIC_ISSUE not found"
        exit 1
    fi
    ISSUE_NUMBERS="$SPECIFIC_ISSUE"
else
    ISSUES=$(gh issue list --repo "$REPO" --state open --json number,title,body,createdAt,comments 2>/dev/null)

    if [ -z "$ISSUES" ] || [ "$ISSUES" = "[]" ]; then
        log "No open issues. All clear!"
        exit 0
    fi

    ISSUE_NUMBERS=$(echo "$ISSUES" | jq -r '.[].number')
fi

# Track state to avoid reprocessing
touch "$STATE_FILE"

for NUM in $ISSUE_NUMBERS; do
    # Skip if already processed (unless specifically requested)
    if [ -z "$SPECIFIC_ISSUE" ] && grep -q "^$NUM$" "$STATE_FILE"; then
        log "Issue #$NUM already processed, skipping..."
        continue
    fi

    # Get issue details
    ISSUE_DATA=$(gh issue view "$NUM" --repo "$REPO" --json number,title,body,comments)
    TITLE=$(echo "$ISSUE_DATA" | jq -r '.title')
    BODY=$(echo "$ISSUE_DATA" | jq -r '.body')
    COMMENTS=$(echo "$ISSUE_DATA" | jq -r '.comments | map(.body) | join("\n---\n")')

    log ""
    log "========================================="
    log "Processing Issue #$NUM: $TITLE"
    log "========================================="

    if [ "$DRY_RUN" = true ]; then
        log "DRY RUN - Would process this issue"
        echo "Title: $TITLE"
        echo "Body preview: ${BODY:0:200}..."
        continue
    fi

    # Read the guidelines
    GUIDELINES=$(cat "$PROMPT_FILE")

    # Build the prompt for Claude
    PROMPT="A GitHub issue needs your attention for the library-manager project.

**Issue #$NUM: $TITLE**

$BODY

$(if [ -n "$COMMENTS" ] && [ "$COMMENTS" != "null" ] && [ "$COMMENTS" != "" ]; then echo "
## Previous Comments
$COMMENTS
"; fi)

## Your Task

1. First, explore the codebase to understand the project structure
2. Analyze this issue - do you fully understand what they're asking?
3. If YES and you can fix it:
   - Implement the fix
   - Update APP_VERSION in app.py (increment beta number)
   - Update CHANGELOG.md
   - Commit with 'Fixes #$NUM' in the message
   - Push to main
   - Comment on issue #$NUM using: gh issue comment $NUM --body \"your message\"
   - Close the issue using: gh issue close $NUM
4. If NO or you need more info:
   - Comment asking for clarification using: gh issue comment $NUM --body \"your question\"
   - DO NOT attempt a fix
   - DO NOT close the issue

Write responses like a real developer - casual and helpful, not formal AI-speak."

    # Run Claude with the prompt
    log "Launching Claude Code..."

    # Use -p for print mode (non-interactive)
    # --dangerously-skip-permissions to auto-approve tool usage
    # --append-system-prompt to add our guidelines
    claude -p "$PROMPT" \
        --dangerously-skip-permissions \
        --append-system-prompt "$GUIDELINES"

    # Mark as processed
    echo "$NUM" >> "$STATE_FILE"

    log "Finished processing issue #$NUM"

    # Small delay between issues
    sleep 5
done

log ""
log "All issues processed!"
