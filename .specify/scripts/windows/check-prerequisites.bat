@echo off
REM Windows batch version of check-prerequisites script for iFlow CLI
REM Consolidated prerequisite checking script
REM
REM Usage: check-prerequisites.bat [OPTIONS]
REM
REM OPTIONS:
REM   /json               Output in JSON format
REM   /require-tasks      Require tasks.md to exist (for implementation phase)
REM   /include-tasks      Include tasks.md in AVAILABLE_DOCS list
REM   /paths-only         Only output path variables (no validation)
REM   /help, /h           Show help message

setlocal enabledelayedexpansion

set JSON=false
set REQUIRE_TASKS=false
set INCLUDE_TASKS=false
set PATHS_ONLY=false

:parse_args
if "%~1"=="" goto :after_parse
if "%~1"=="/json" (
    set JSON=true
    shift
    goto :parse_args
)
if "%~1"=="/require-tasks" (
    set REQUIRE_TASKS=true
    shift
    goto :parse_args
)
if "%~1"=="/include-tasks" (
    set INCLUDE_TASKS=true
    shift
    goto :parse_args
)
if "%~1"=="/paths-only" (
    set PATHS_ONLY=true
    shift
    goto :parse_args
)
if "%~1"=="/help" (
    call :show_help
    exit /b 0
)
if "%~1"=="/h" (
    call :show_help
    exit /b 0
)
echo Unknown option: %~1
call :show_help
exit /b 1

:after_parse

REM Source common functions
for %%i in ("%~dp0common.bat") do call "%%i"

REM Get feature paths and validate branch
call :get_feature_paths_env

if not test_feature_branch "%CURRENT_BRANCH%" "%HAS_GIT%" (
    exit /b 1
)

REM If paths-only mode, output paths and exit
if "%PATHS_ONLY%"=="true" (
    if "%JSON%"=="true" (
        echo {"REPO_ROOT":"%REPO_ROOT%","BRANCH":"%CURRENT_BRANCH%","FEATURE_DIR":"%FEATURE_DIR%","FEATURE_SPEC":"%FEATURE_SPEC%","IMPL_PLAN":"%IMPL_PLAN%","TASKS":"%TASKS%"}
    ) else (
        echo REPO_ROOT: %REPO_ROOT%
        echo BRANCH: %CURRENT_BRANCH%
        echo FEATURE_DIR: %FEATURE_DIR%
        echo FEATURE_SPEC: %FEATURE_SPEC%
        echo IMPL_PLAN: %IMPL_PLAN%
        echo TASKS: %TASKS%
    )
    exit /b 0
)

REM Validate required directories and files
if not exist "%FEATURE_DIR%\" (
    echo ERROR: Feature directory not found: %FEATURE_DIR%
    echo Run /speckit.specify first to create the feature structure.
    exit /b 1
)

if not exist "%IMPL_PLAN%" (
    echo ERROR: plan.md not found in %FEATURE_DIR%
    echo Run /speckit.plan first to create the implementation plan.
    exit /b 1
)

REM Check for tasks.md if required
if "%REQUIRE_TASKS%"=="true" if not exist "%TASKS%" (
    echo ERROR: tasks.md not found in %FEATURE_DIR%
    echo Run /speckit.tasks first to create the task list.
    exit /b 1
)

REM Build list of available documents
set docs=

REM Always check these optional docs
if exist "%RESEARCH%" set docs=!docs! "research.md"
if exist "%DATA_MODEL%" set docs=!docs! "data-model.md"

REM Check contracts directory (only if it exists and has files)
if exist "%CONTRACTS_DIR%\" (
    dir /b "%CONTRACTS_DIR%" >nul 2>&1
    if !errorlevel! equ 0 set docs=!docs! "contracts/"
)

if exist "%QUICKSTART%" set docs=!docs! "quickstart.md"

REM Include tasks.md if requested and it exists
if "%INCLUDE_TASKS%"=="true" if exist "%TASKS%" set docs=!docs! "tasks.md"

REM Output results
if "%JSON%"=="true" (
    REM JSON output - build array manually
    set json_docs=[]
    for %%d in (!docs!) do (
        set "json_docs=!json_docs!,%%~d"
    )
    set "json_docs=!json_docs:~1!"
    echo {"FEATURE_DIR":"%FEATURE_DIR%","AVAILABLE_DOCS":!json_docs!}
) else (
    REM Text output
    echo FEATURE_DIR:%FEATURE_DIR%
    echo AVAILABLE_DOCS:
    
    REM Show status of each potential document
    call :test_file_exists "%RESEARCH%" "research.md"
    call :test_file_exists "%DATA_MODEL%" "data-model.md"
    call :test_dir_has_files "%CONTRACTS_DIR%" "contracts/"
    call :test_file_exists "%QUICKSTART%" "quickstart.md"
    
    if "%INCLUDE_TASKS%"=="true" call :test_file_exists "%TASKS%" "tasks.md"
)

goto :eof

:show_help
echo Usage: check-prerequisites.bat [OPTIONS]
echo.
echo Consolidated prerequisite checking for Spec-Driven Development workflow.
echo.
echo OPTIONS:
echo   /json               Output in JSON format
echo   /require-tasks      Require tasks.md to exist (for implementation phase)
echo   /include-tasks      Include tasks.md in AVAILABLE_DOCS list
echo   /paths-only         Only output path variables (no prerequisite validation)
echo   /help, /h           Show this help message
echo.
echo EXAMPLES:
echo   # Check task prerequisites (plan.md required)
echo   check-prerequisites.bat /json
echo.
echo   # Check implementation prerequisites (plan.md + tasks.md required)
echo   check-prerequisites.bat /json /require-tasks /include-tasks
echo.
echo   # Get feature paths only (no validation)
echo   check-prerequisites.bat /paths-only
goto :eof