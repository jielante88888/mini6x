#!/usr/bin/env python3
"""
CI配置验证脚本
用于验证加密货币交易终端项目的CI设置是否正确配置
"""
import os
import json
import subprocess
import yaml
from pathlib import Path

def check_file_exists(file_path):
    """检查文件是否存在"""
    return Path(file_path).exists()

def check_github_workflows():
    """检查GitHub Actions工作流配置"""
    workflows_dir = Path(".github/workflows")
    required_workflows = [
        "ci.yml",
        "coverage.yml", 
        "release.yml",
        "security.yml"
    ]
    
    results = {}
    for workflow in required_workflows:
        workflow_path = workflows_dir / workflow
        if workflow_path.exists():
            try:
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                    # 检查Python版本是否为3.14
                    python_version = None
                    if 'jobs' in content:
                        for job_name, job_config in content['jobs'].items():
                            if 'steps' in job_config:
                                for step in job_config['steps']:
                                    if 'uses' in step and 'setup-python' in step['uses']:
                                        python_version = step.get('with', {}).get('python-version', 'unknown')
                                        break
                    results[workflow] = {
                        'exists': True,
                        'python_version': python_version,
                        'status': '✅ 配置正确' if python_version == '3.14' else f'⚠️  Python版本: {python_version}'
                    }
            except Exception as e:
                results[workflow] = {
                    'exists': True,
                    'python_version': '解析错误',
                    'status': f'❌ 错误: {str(e)}'
                }
        else:
            results[workflow] = {
                'exists': False,
                'python_version': 'N/A',
                'status': '❌ 文件不存在'
            }
    
    return results

def check_docker_files():
    """检查Docker相关文件"""
    docker_files = {
        'Dockerfile': 'Docker容器构建配置',
        '.dockerignore': 'Docker忽略文件配置'
    }
    
    results = {}
    for file_name, description in docker_files.items():
        if check_file_exists(file_name):
            results[file_name] = {
                'exists': True,
                'description': description,
                'status': '✅ 存在'
            }
        else:
            results[file_name] = {
                'exists': False,
                'description': description,
                'status': '❌ 不存在'
            }
    
    return results

def check_git_config():
    """检查Git配置"""
    try:
        # 检查远程仓库
        result = subprocess.run(['git', 'remote', '-v'], 
                              capture_output=True, text=True, check=False)
        remote_output = result.stdout.strip()
        
        # 检查分支
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, check=False)
        current_branch = result.stdout.strip()
        
        return {
            'remote_configured': 'origin' in remote_output,
            'remote_url': remote_output.split('\n')[0] if remote_output else None,
            'current_branch': current_branch,
            'status': '✅ Git配置正确' if 'origin' in remote_output else '⚠️  远程仓库未配置'
        }
    except Exception as e:
        return {
            'remote_configured': False,
            'current_branch': 'unknown',
            'status': f'❌ Git错误: {str(e)}'
        }

def main():
    """主验证函数"""
    print("🚀 开始验证CI配置...")
    print("=" * 60)
    
    # 检查项目文件
    print("\n📁 检查项目文件:")
    project_files = {
        'requirements.txt': 'Python依赖配置',
        '.gitignore': 'Git忽略文件',
        'ci.md': 'CI配置说明文档',
        '加密货币专业交易终端系统完整方案.md': '项目方案文档'
    }
    
    for file_name, description in project_files.items():
        exists = check_file_exists(file_name)
        status = "✅ 存在" if exists else "❌ 不存在"
        print(f"  {file_name:50} {status}")
    
    # 检查GitHub Actions工作流
    print("\n🔧 检查GitHub Actions工作流:")
    workflows = check_github_workflows()
    for workflow, info in workflows.items():
        print(f"  {workflow:20} {info['status']}")
        if info['exists'] and info['python_version']:
            print(f"    Python版本: {info['python_version']}")
    
    # 检查Docker文件
    print("\n🐳 检查Docker配置:")
    docker_files = check_docker_files()
    for file_name, info in docker_files.items():
        print(f"  {file_name:20} {info['status']}")
    
    # 检查Git配置
    print("\n📋 检查Git配置:")
    git_info = check_git_config()
    print(f"  远程仓库配置: {'✅ 已配置' if git_info['remote_configured'] else '❌ 未配置'}")
    if git_info.get('remote_url'):
        print(f"  仓库地址: {git_info['remote_url']}")
    print(f"  当前分支: {git_info['current_branch']}")
    print(f"  状态: {git_info['status']}")
    
    # 检查Flutter配置
    print("\n🎯 检查Flutter配置:")
    flutter_exists = check_file_exists('pubspec.yaml')
    print(f"  pubspec.yaml: {'✅ 存在' if flutter_exists else '❌ 不存在'}")
    
    print("\n" + "=" * 60)
    print("✅ CI配置验证完成!")
    
    # 生成建议
    print("\n💡 后续操作建议:")
    print("1. 推送代码到GitHub仓库: git push -u origin master")
    print("2. 在GitHub仓库设置中配置Secrets:")
    print("   - DOCKER_USERNAME")
    print("   - DOCKER_PASSWORD") 
    print("   - BINANCE_API_KEY (币安API密钥)")
    print("   - BINANCE_SECRET_KEY (币安密钥)")
    print("   - OKX_API_KEY (OKX API密钥)")
    print("   - OKX_SECRET_KEY (OKX密钥)")
    print("3. 启用GitHub Actions工作流")
    print("4. 使用标签 '[test-api]' 触发API测试:")
    print("   git commit -m 'test API connections [test-api]'")
    print("5. 使用标签 '[docker]' 触发Docker构建:")
    print("   git commit -m 'build Docker images [docker]'")

if __name__ == "__main__":
    main()