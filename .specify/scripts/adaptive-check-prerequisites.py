#!/usr/bin/env python3
"""
Adaptive check-prerequisites script for iFlow CLI
Automatically detects system and runs appropriate script version
"""

import os
import sys
import subprocess
import platform

def detect_system():
    """Detect the current operating system"""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system in ["linux", "darwin"]:  # macOS and Linux
        return "bash"
    else:
        # Fallback to bash on Unix-like systems
        return "bash"

def run_script(script_path, args):
    """Run the appropriate script with given arguments"""
    try:
        if platform.system().lower() == "windows":
            # Windows batch script
            cmd = ["cmd", "/c", script_path] + args
        else:
            # Bash script
            cmd = ["bash", script_path] + args
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.dirname(script_path))))
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def main():
    if len(sys.argv) < 2:
        print("Usage: adaptive-check-prerequisites.py <script_args...>")
        sys.exit(1)
    
    system = detect_system()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if system == "windows":
        script_path = os.path.join(script_dir, "windows", "check-prerequisites.bat")
    else:
        script_path = os.path.join(script_dir, "bash", "check-prerequisites.sh")
    
    args = sys.argv[1:]
    returncode, stdout, stderr = run_script(script_path, args)
    
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)
    
    sys.exit(returncode)

if __name__ == "__main__":
    main()