#!/bin/bash

# Bash version of check-prerequisites script for iFlow CLI
# Consolidated prerequisite checking script
#
# Usage: ./check-prerequisites.sh [OPTIONS]
#
# OPTIONS:
#   --json               Output in JSON format
#   --require-tasks      Require tasks.md to exist (for implementation phase)
#   --include-tasks      Include tasks.md in AVAILABLE_DOCS list
#   --paths-only         Only output path variables (no validation)
#   --help, -h           Show help message

set -e

show_help() {
    cat << EOF
Usage: check-prerequisites.sh [OPTIONS]

Consolidated prerequisite checking for Spec-Driven Development workflow.

OPTIONS:
  --json               Output in JSON format
  --require-tasks      Require tasks.md to exist (for implementation phase)
  --include-tasks      Include tasks.md in AVAILABLE_DOCS list
  --paths-only         Only output path variables (no prerequisite validation)
  --help, -h           Show this help message

EXAMPLES:
  # Check task prerequisites (plan.md required)
  ./check-prerequisites.sh --json
  
  # Check implementation prerequisites (plan.md + tasks.md required)
  ./check-prerequisites.sh --json --require-tasks --include-tasks
  
  # Get feature paths only (no validation)
  ./check-prerequisites.sh --paths-only
EOF
    exit 0
}

# Parse arguments
JSON=false
REQUIRE_TASKS=false
INCLUDE_TASKS=false
PATHS_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON=true
            shift
            ;;
        --require-tasks)
            REQUIRE_TASKS=true
            shift
            ;;
        --include-tasks)
            INCLUDE_TASKS=true
            shift
            ;;
        --paths-only)
            PATHS_ONLY=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get feature paths and validate branch
eval "$(get_feature_paths_env)"

if ! test_feature_branch "$CURRENT_BRANCH" "$HAS_GIT"; then 
    exit 1 
fi

# If paths-only mode, output paths and exit
if [[ "$PATHS_ONLY" == "true" ]]; then
    if [[ "$JSON" == "true" ]]; then
        echo "{\"REPO_ROOT\":\"$REPO_ROOT\",\"BRANCH\":\"$CURRENT_BRANCH\",\"FEATURE_DIR\":\"$FEATURE_DIR\",\"FEATURE_SPEC\":\"$FEATURE_SPEC\",\"IMPL_PLAN\":\"$IMPL_PLAN\",\"TASKS\":\"$TASKS\"}"
    else
        echo "REPO_ROOT: $REPO_ROOT"
        echo "BRANCH: $CURRENT_BRANCH"
        echo "FEATURE_DIR: $FEATURE_DIR"
        echo "FEATURE_SPEC: $FEATURE_SPEC"
        echo "IMPL_PLAN: $IMPL_PLAN"
        echo "TASKS: $TASKS"
    fi
    exit 0
fi

# Validate required directories and files
if [[ ! -d "$FEATURE_DIR" ]]; then
    echo "ERROR: Feature directory not found: $FEATURE_DIR"
    echo "Run /speckit.specify first to create the feature structure."
    exit 1
fi

if [[ ! -f "$IMPL_PLAN" ]]; then
    echo "ERROR: plan.md not found in $FEATURE_DIR"
    echo "Run /speckit.plan first to create the implementation plan."
    exit 1
fi

# Check for tasks.md if required
if [[ "$REQUIRE_TASKS" == "true" ]] && [[ ! -f "$TASKS" ]]; then
    echo "ERROR: tasks.md not found in $FEATURE_DIR"
    echo "Run /speckit.tasks first to create the task list."
    exit 1
fi

# Build list of available documents
docs=()

# Always check these optional docs
[[ -f "$RESEARCH" ]] && docs+=("research.md")
[[ -f "$DATA_MODEL" ]] && docs+=("data-model.md")

# Check contracts directory (only if it exists and has files)
if [[ -d "$CONTRACTS_DIR" ]] && [[ -n "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ]]; then 
    docs+=("contracts/") 
fi

[[ -f "$QUICKSTART" ]] && docs+=("quickstart.md")

# Include tasks.md if requested and it exists
if [[ "$INCLUDE_TASKS" == "true" ]] && [[ -f "$TASKS" ]]; then 
    docs+=("tasks.md") 
fi

# Output results
if [[ "$JSON" == "true" ]]; then
    echo "{\"FEATURE_DIR\":\"$FEATURE_DIR\",\"AVAILABLE_DOCS\":[$(printf '"%s",' "${docs[@]}" | sed 's/,$//')]}"
else
    echo "FEATURE_DIR:$FEATURE_DIR"
    echo "AVAILABLE_DOCS:"
    
    # Show status of each potential document
    test_file_exists "$RESEARCH" "research.md" || true
    test_file_exists "$DATA_MODEL" "data-model.md" || true
    test_dir_has_files "$CONTRACTS_DIR" "contracts/" || true
    test_file_exists "$QUICKSTART" "quickstart.md" || true
    
    if [[ "$INCLUDE_TASKS" == "true" ]]; then
        test_file_exists "$TASKS" "tasks.md" || true
    fi
fi