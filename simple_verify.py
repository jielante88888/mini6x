#!/usr/bin/env python3
"""
简化版CI配置验证脚本
"""
import os
import json
import subprocess
from pathlib import Path

def check_github_workflows():
    """检查GitHub Actions工作流配置"""
    workflows_dir = Path(".github/workflows")
    required_workflows = [
        "ci.yml",
        "coverage.yml", 
        "release.yml",
        "security.yml"
    ]
    
    print("🔧 检查GitHub Actions工作流:")
    for workflow in required_workflows:
        workflow_path = workflows_dir / workflow
        if workflow_path.exists():
            try:
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'python-version: \'3.14\'' in content:
                        status = '✅ Python 3.14'
                    elif 'python-version: \'3.11\'' in content:
                        status = '⚠️  Python 3.11'
                    else:
                        status = '⚠️  版本未知'
                    print(f"  {workflow:20} {status}")
            except Exception as e:
                print(f"  {workflow:20} ❌ 解析错误")
        else:
            print(f"  {workflow:20} ❌ 文件不存在")

def check_docker_files():
    """检查Docker相关文件"""
    print("\n🐳 检查Docker配置:")
    docker_files = {
        'Dockerfile': False,
        '.dockerignore': False
    }
    
    for file_name in docker_files:
        if Path(file_name).exists():
            docker_files[file_name] = True
            print(f"  {file_name:20} ✅ 存在")
        else:
            print(f"  {file_name:20} ❌ 不存在")

def check_git_config():
    """检查Git配置"""
    print("\n📋 检查Git配置:")
    try:
        result = subprocess.run(['git', 'remote', '-v'], 
                              capture_output=True, text=True, check=False)
        remote_output = result.stdout.strip()
        
        if 'origin' in remote_output:
            print(f"  远程仓库配置: ✅ 已配置")
            print(f"  仓库地址: {remote_output.split()[1]}")
        else:
            print(f"  远程仓库配置: ❌ 未配置")
            
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, check=False)
        current_branch = result.stdout.strip()
        print(f"  当前分支: {current_branch}")
        
    except Exception as e:
        print(f"  Git错误: {str(e)}")

def main():
    """主验证函数"""
    print("🚀 CI配置验证报告")
    print("=" * 50)
    
    # 检查基础项目文件
    print("\n📁 项目文件检查:")
    project_files = [
        'requirements.txt',
        '.gitignore', 
        'ci.md',
        '加密货币专业交易终端系统完整方案.md',
        '.github/workflows/ci.yml',
        '.github/workflows/coverage.yml',
        '.github/workflows/release.yml', 
        '.github/workflows/security.yml',
        'Dockerfile',
        '.dockerignore'
    ]
    
    for file_path in project_files:
        exists = Path(file_path).exists()
        status = "✅" if exists else "❌"
        print(f"  {file_path:45} {status}")
    
    # 检查工作流配置
    check_github_workflows()
    
    # 检查Docker文件
    check_docker_files()
    
    # 检查Git配置
    check_git_config()
    
    print("\n" + "=" * 50)
    print("✅ CI配置验证完成!")

if __name__ == "__main__":
    main()