#!/usr/bin/env python3
"""
ThoughtLens - Cross-Platform Installer
Run: python install.py
"""

import subprocess
import sys
import os
import platform
import shutil
from pathlib import Path

# Colors for terminal
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RED = '\033[91m'
BOLD = '\033[1m'
NC = '\033[0m'

def print_banner():
    print(f"""{CYAN}{BOLD}
   ######## ##     ## ########  ##     ##  ######   ##     ## ########
       ##    ##     ## ##     ## ##     ## ##    ##  ##     ##    ##
       ##    ##     ## ##     ## ##     ## ##        ##     ##    ##
       ##    ######### ##     ## ##     ## ##   #### #########    ##
       ##    ##     ## ##     ## ##     ## ##    ##  ##     ##    ##
       ##    ##     ## ##     ## ##     ## ##    ##  ##     ##    ##
       ##    ##     ##  #######   #######   ######   ##     ##    ##

        ##       ######## ##    ##  ######
        ##       ##       ###   ## ##    ##
        ##       ##       ####  ## ##
        ##       ######   ## ## ##  ######
        ##       ##       ##  ####       ##
        ##       ##       ##   ### ##    ##
        ######## ########  ##    ##  ######
{NC}{CYAN}           I N S T A L L E R{NC}
""")

def run_cmd(cmd, cwd=None, capture=False):
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
            return result.returncode == 0, result.stdout.strip()
        else:
            result = subprocess.run(cmd, shell=True, cwd=cwd)
            return result.returncode == 0, ""
    except Exception as e:
        print(f"{RED}  Error: {e}{NC}")
        return False, ""

def check_prerequisites():
    print(f"{YELLOW}  Checking prerequisites...{NC}")
    missing = []
    
    # Check Python
    if sys.version_info < (3, 11):
        missing.append("Python 3.11+")
    
    # Check npm
    success, _ = run_cmd("npm --version", capture=True)
    if not success:
        missing.append("Node.js (npm)")
    
    # Check git
    success, _ = run_cmd("git --version", capture=True)
    if not success:
        missing.append("Git")
    
    if missing:
        print(f"{RED}  Missing: {', '.join(missing)}{NC}")
        print(f"\n  Please install missing tools and re-run.")
        return False
    
    print(f"{GREEN}  + All prerequisites found{NC}")
    return True

def setup_lobstertrap():
    print(f"{CYAN}  [1/4] Setting up Lobster Trap...{NC}")
    
    lobster_dir = Path("../lobstertrap")
    repo_url = "https://github.com/VeeaTech/lobstertrap.git"
    
    if lobster_dir.exists():
        print(f"{YELLOW}        + Lobster Trap already exists, updating...{NC}")
        run_cmd("git pull", cwd=lobster_dir)
    else:
        print(f"{YELLOW}        + Cloning Lobster Trap repository...{NC}")
        success, _ = run_cmd(f"git clone {repo_url} {lobster_dir}")
        if not success:
            print(f"{RED}        + Clone failed{NC}")
            return False
    
    # Build Lobster Trap
    print(f"{YELLOW}        + Building Lobster Trap...{NC}")
    if platform.system() == "Windows":
        success, _ = run_cmd("go build -o lobstertrap.exe", cwd=lobster_dir)
        binary = lobster_dir / "lobstertrap.exe"
    else:
        success, _ = run_cmd("go build -o lobstertrap", cwd=lobster_dir)
        binary = lobster_dir / "lobstertrap"
    
    if success and binary.exists():
        print(f"{GREEN}        + Lobster Trap built successfully{NC}")
        return True
    else:
        print(f"{YELLOW}        + Go not found. Lobster Trap not built (optional){NC}")
        return True  # Not fatal

def install_python_deps():
    print(f"{CYAN}  [2/4] Installing Python dependencies...{NC}")
    
    deps = [
        "fastapi",
        "uvicorn[standard]",
        "httpx",
        "Pillow",
        "piexif",
        "pydantic",
        "pydantic-settings",
        "python-multipart",
        "python-dotenv"
    ]
    
    for dep in deps:
        print(f"{YELLOW}        + Installing {dep}...{NC}")
        run_cmd(f"{sys.executable} -m pip install {dep} --quiet")
    
    # Install from pyproject.toml
    if Path("pyproject.toml").exists():
        print(f"{YELLOW}        + Installing from pyproject.toml...{NC}")
        run_cmd(f"{sys.executable} -m pip install -e . --quiet")
    
    print(f"{GREEN}        + Python dependencies installed{NC}")
    return True

def install_ui_deps():
    print(f"{CYAN}  [3/4] Installing UI dependencies...{NC}")
    
    ui_dir = Path("ui")
    if not ui_dir.exists():
        print(f"{RED}        + UI directory not found{NC}")
        return False
    
    if (ui_dir / "node_modules").exists():
        print(f"{YELLOW}        + node_modules exists, checking updates...{NC}")
        run_cmd("npm install", cwd=ui_dir)
    else:
        print(f"{YELLOW}        + Installing npm packages...{NC}")
        run_cmd("npm install", cwd=ui_dir)
    
    print(f"{GREEN}        + UI dependencies installed{NC}")
    return True

def create_env_file():
    print(f"{CYAN}  [4/4] Configuring environment...{NC}")
    
    env_file = Path(".env")
    if not env_file.exists():
        print(f"{YELLOW}        + Creating .env from template...{NC}")
        
        env_content = '''# ThoughtLens Configuration
TL_PORT=8000
TL_LLM_URL=https://api.groq.com/openai/v1
TL_LLM_KEY=your_api_key_here
TL_LT_PORT=8080
TL_LT_BINARY=./lobstertrap/lobstertrap
TL_LT_POLICY=./configs/thoughtlens_policy.yaml
TL_LOG_LEVEL=info

# PRISM Configuration
PRISM_PROVIDER=https://api.groq.com/openai/v1
PRISM_KEY=your_api_key_here
PRISM_MODEL=llama-3.1-8b-instant

# Agent defaults
AGENT_URL=http://localhost:8000/v1/messages
AGENT_MODEL=llama-3.1-8b-instant

# Optional: Anthropic for Explain feature
VITE_ANTHROPIC_API_KEY=
'''
        env_file.write_text(env_content)
        print(f"{YELLOW}        + .env created. Edit it to add your API keys!{NC}")
    else:
        print(f"{GREEN}        + .env already exists{NC}")
    return True

def verify_installation():
    print(f"{CYAN}  Verifying installation...{NC}")
    
    all_good = True
    
    # Check Python packages
    try:
        import fastapi, uvicorn, httpx, PIL, piexif
        print(f"{GREEN}        + Python packages OK{NC}")
    except ImportError as e:
        print(f"{RED}        + Python packages FAILED: {e}{NC}")
        all_good = False
    
    # Check Lobster Trap
    if Path("../lobstertrap/lobstertrap.exe").exists() or Path("../lobstertrap/lobstertrap").exists():
        print(f"{GREEN}        + Lobster Trap OK{NC}")
    elif Path("lobstertrap/lobstertrap.exe").exists() or Path("lobstertrap/lobstertrap").exists():
        print(f"{GREEN}        + Lobster Trap OK{NC}")
    else:
        print(f"{YELLOW}        + Lobster Trap not found (optional){NC}")
    
    # Check UI
    if Path("ui/node_modules").exists():
        print(f"{GREEN}        + UI dependencies OK{NC}")
    else:
        print(f"{RED}        + UI dependencies FAILED{NC}")
        all_good = False
    
    return all_good

def main():
    print_banner()
    print(f"  {'-' * 74}\n")
    
    if not check_prerequisites():
        sys.exit(1)
    print()
    
    if not setup_lobstertrap():
        print(f"{YELLOW}  Continuing without Lobster Trap...{NC}")
    print()
    
    if not install_python_deps():
        print(f"{RED}  Python dependency installation failed{NC}")
        sys.exit(1)
    print()
    
    if not install_ui_deps():
        print(f"{RED}  UI dependency installation failed{NC}")
        sys.exit(1)
    print()
    
    create_env_file()
    print()
    
    print(f"  {'-' * 74}\n")
    
    if verify_installation():
        print(f"{GREEN}{BOLD}  Installation complete!{NC}")
        print()
        print(f"  Next steps:")
        print(f"    1. Edit .env and add your API keys")
        print(f"    2. Run: {YELLOW}python start.py{NC} or {YELLOW}./start.sh{NC} or {YELLOW}start.bat{NC}")
        print(f"    3. Run agent: {YELLOW}python demo/interactive_agent.py{NC}")
    else:
        print(f"{RED}{BOLD}  Installation had issues. Please check the errors above.{NC}")
    
    print()
    print(f"  {'-' * 74}\n")

if __name__ == "__main__":
    main()