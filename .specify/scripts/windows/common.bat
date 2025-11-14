@echo off
REM Common Windows batch functions for iFlow CLI adaptation

setlocal enabledelayedexpansion

:function get_repo_root
    REM First try git
    git rev-parse --show-toplevel 2>nul
    if !errorlevel! equ 0 (
        for /f "delims=" %%i in ('git rev-parse --show-toplevel 2^>nul') do set "REPO_ROOT=%%i"
        goto :eof
    )
    
    REM Fall back to script location for non-git repos
    set "SCRIPT_DIR=%~dp0"
    set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"
    for %%i in ("!SCRIPT_DIR!\..\..\..") do set "REPO_ROOT=%%~fi"
    goto :eof
:endfunction

:function get_current_branch
    REM First check if SPECIFY_FEATURE environment variable is set
    if defined SPECIFY_FEATURE (
        echo !SPECIFY_FEATURE!
        goto :eof
    )
    
    REM Then check git if available
    git rev-parse --abbrev-ref HEAD 2>nul >tmp_branch.txt
    if !errorlevel! equ 0 (
        set /p CURRENT_BRANCH=<tmp_branch.txt
        del tmp_branch.txt
        echo !CURRENT_BRANCH!
        goto :eof
    )
    del tmp_branch.txt 2>nul
    
    REM For non-git repos, try to find the latest feature directory
    call :get_repo_root
    set "SPECS_DIR=!REPO_ROOT!\specs"
    
    if exist "!SPECS_DIR!\" (
        set "LATEST_FEATURE="
        set "HIGHEST=0"
        
        for /d %%d in ("!SPECS_DIR!\*") do (
            set "BASENAME=%%~nd"
            echo !BASENAME! | findstr /r "^[0-9][0-9][0-9]-" >nul
            if !errorlevel! equ 0 (
                for /f "tokens=1 delims=-" %%n in ("!BASENAME!") do (
                    if %%n gtr !HIGHEST! (
                        set "HIGHEST=%%n"
                        set "LATEST_FEATURE=!BASENAME!"
                    )
                )
            )
        )
        
        if defined LATEST_FEATURE (
            echo !LATEST_FEATURE!
            goto :eof
        )
    )
    
    REM Final fallback
    echo main
    goto :eof
:endfunction

:function test_has_git
    git rev-parse --show-toplevel 2>nul >nul
endfunction & set "HAS_GIT=%errorlevel%"

:function test_feature_branch
    set "BRANCH=%~1"
    set "HAS_GIT=%~2"
    
    REM For non-git repos, we can't enforce branch naming but still provide output
    if "%HAS_GIT%" neq "0" (
        echo [specify] Warning: Git repository not detected; skipped branch validation >&2
        goto :eof
    )
    
    echo %BRANCH% | findstr /r "^[0-9][0-9][0-9]-" >nul
    if !errorlevel! neq 0 (
        echo ERROR: Not on a feature branch. Current branch: %BRANCH% >&2
        echo Feature branches should be named like: 001-feature-name >&2
        set "TEST_RESULT=1"
        goto :eof
    )
    
    set "TEST_RESULT=0"
    goto :eof
:endfunction

:function get_feature_dir
    set "REPO_ROOT=%~1"
    set "BRANCH=%~2"
    set "FEATURE_DIR=%REPO_ROOT%\specs\%BRANCH%"
    goto :eof
:endfunction

:function get_feature_paths_env
    call :get_repo_root
    call :get_current_branch
    call :test_has_git
    call :get_feature_dir "%REPO_ROOT%" "%CURRENT_BRANCH%"
    
    echo REPO_ROOT='%REPO_ROOT%'
    echo CURRENT_BRANCH='%CURRENT_BRANCH%'
    echo HAS_GIT='%HAS_GIT%'
    echo FEATURE_DIR='%FEATURE_DIR%'
    echo FEATURE_SPEC='%FEATURE_DIR%\spec.md'
    echo IMPL_PLAN='%FEATURE_DIR%\plan.md'
    echo TASKS='%FEATURE_DIR%\tasks.md'
    echo RESEARCH='%FEATURE_DIR%\research.md'
    echo DATA_MODEL='%FEATURE_DIR%\data-model.md'
    echo QUICKSTART='%FEATURE_DIR%\quickstart.md'
    echo CONTRACTS_DIR='%FEATURE_DIR%\contracts'
    goto :eof
:endfunction

:function test_file_exists
    set "PATH=%~1"
    set "DESCRIPTION=%~2"
    if exist "%PATH%" (
        echo   ✓ %DESCRIPTION%
        set "FILE_EXISTS=1"
    ) else (
        echo   ✗ %DESCRIPTION%
        set "FILE_EXISTS=0"
    )
    goto :eof
:endfunction

:function test_dir_has_files
    set "PATH=%~1"
    set "DESCRIPTION=%~2"
    if exist "%PATH%\" (
        dir /b "%PATH%" >nul 2>&1
        if !errorlevel! equ 0 (
            echo   ✓ %DESCRIPTION%
            set "DIR_EXISTS=1"
        ) else (
            echo   ✗ %DESCRIPTION%
            set "DIR_EXISTS=0"
        )
    ) else (
        echo   ✗ %DESCRIPTION%
        set "DIR_EXISTS=0"
    )
    goto :eof
:endfunction