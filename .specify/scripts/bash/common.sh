#!/bin/bash
# Common Bash functions for iFlow CLI adaptation

function get_repo_root {
    # First try git
    if git rev-parse --show-toplevel 2>/dev/null; then
        return 0
    fi
    
    # Fall back to script location for non-git repos
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "$(cd "$script_dir/../../.." && pwd)"
}

function get_current_branch {
    # First check if SPECIFY_FEATURE environment variable is set
    if [[ -n "$SPECIFY_FEATURE" ]]; then
        echo "$SPECIFY_FEATURE"
        return 0
    fi
    
    # Then check git if available
    local git_branch
    if git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null); then
        echo "$git_branch"
        return 0
    fi
    
    # For non-git repos, try to find the latest feature directory
    local repo_root=$(get_repo_root)
    local specs_dir="$repo_root/specs"
    
    if [[ -d "$specs_dir" ]]; then
        local latest_feature=""
        local highest=0
        
        for dir in "$specs_dir"/*/; do
            if [[ -d "$dir" ]]; then
                local basename=$(basename "$dir")
                if [[ "$basename" =~ ^([0-9]{3})- ]]; then
                    local num="${BASH_REMATCH[1]}"
                    if [[ $num -gt $highest ]]; then
                        highest=$num
                        latest_feature="$basename"
                    fi
                fi
            fi
        done
        
        if [[ -n "$latest_feature" ]]; then
            echo "$latest_feature"
            return 0
        fi
    fi
    
    # Final fallback
    echo "main"
}

function test_has_git {
    git rev-parse --show-toplevel 2>/dev/null >/dev/null
}

function test_feature_branch {
    local branch="$1"
    local has_git="$2"
    
    # For non-git repos, we can't enforce branch naming but still provide output
    if [[ "$has_git" != "true" ]]; then
        echo "[specify] Warning: Git repository not detected; skipped branch validation" >&2
        return 0
    fi
    
    if [[ ! "$branch" =~ ^[0-9]{3}- ]]; then
        echo "ERROR: Not on a feature branch. Current branch: $branch" >&2
        echo "Feature branches should be named like: 001-feature-name" >&2
        return 1
    fi
    return 0
}

function get_feature_dir {
    local repo_root="$1"
    local branch="$2"
    echo "$repo_root/specs/$branch"
}

function get_feature_paths_env {
    local repo_root=$(get_repo_root)
    local current_branch=$(get_current_branch)
    local has_git="false"
    local feature_dir
    
    if test_has_git; then
        has_git="true"
    fi
    
    feature_dir=$(get_feature_dir "$repo_root" "$current_branch")
    
    echo "REPO_ROOT='$repo_root'"
    echo "CURRENT_BRANCH='$current_branch'"
    echo "HAS_GIT='$has_git'"
    echo "FEATURE_DIR='$feature_dir'"
    echo "FEATURE_SPEC='$feature_dir/spec.md'"
    echo "IMPL_PLAN='$feature_dir/plan.md'"
    echo "TASKS='$feature_dir/tasks.md'"
    echo "RESEARCH='$feature_dir/research.md'"
    echo "DATA_MODEL='$feature_dir/data-model.md'"
    echo "QUICKSTART='$feature_dir/quickstart.md'"
    echo "CONTRACTS_DIR='$feature_dir/contracts'"
}

function test_file_exists {
    local path="$1"
    local description="$2"
    if [[ -f "$path" ]]; then
        echo "  ✓ $description"
        return 0
    else
        echo "  ✗ $description"
        return 1
    fi
}

function test_dir_has_files {
    local path="$1"
    local description="$2"
    if [[ -d "$path" ]] && [[ -n "$(ls -A "$path" 2>/dev/null)" ]]; then
        echo "  ✓ $description"
        return 0
    else
        echo "  ✗ $description"
        return 1
    fi
}