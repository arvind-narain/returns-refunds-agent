#!/usr/bin/env python3
"""
File Cleanup Script: Safely delete generated files and configurations

This script deletes:
- Python scripts (01-25)
- Config JSON files
- Runtime configuration files
- Docker files
- Requirements files
- Generated agent files
- .bedrock_agentcore.yaml file
"""

import os
import time
from pathlib import Path
from typing import List

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Base directory
BASE_DIR = Path(".")
SCRIPTS_DIR = BASE_DIR / "scripts"


def safe_delete_file(file_path: Path) -> bool:
    """Safely delete a file with error handling"""
    try:
        if file_path.exists():
            file_path.unlink()
            print(f"{GREEN}✓ Deleted: {file_path}{RESET}")
            return True
        else:
            print(f"{YELLOW}⊘ Not found: {file_path}{RESET}")
            return False
    except Exception as e:
        print(f"{RED}✗ Failed to delete {file_path}: {e}{RESET}")
        return False


def get_files_to_delete() -> List[Path]:
    """Get list of all files to delete"""
    files = []
    
    # Python scripts (01-25)
    for i in range(1, 26):
        script_name = f"{i:02d}_*.py"
        matching_files = list(SCRIPTS_DIR.glob(script_name))
        files.extend(matching_files)
    
    # Config JSON files
    config_files = [
        "runtime_config.json",
        "gateway_config.json",
        "memory_config.json",
        "lambda_config.json",
        "cognito_config.json",
        "runtime_execution_role_config.json",
        "gateway_role_config.json",
        "kb_config.json"
    ]
    files.extend([BASE_DIR / f for f in config_files])
    
    # Docker files
    docker_files = [
        "Dockerfile",
        ".dockerignore"
    ]
    files.extend([BASE_DIR / f for f in docker_files])
    
    # Requirements files
    requirements_files = [
        "requirements.txt",
        "requirements_streamlit.txt"
    ]
    files.extend([BASE_DIR / f for f in requirements_files])
    
    # Generated agent files
    agent_files = list((BASE_DIR / "src" / "agents").glob("*_agent.py"))
    files.extend(agent_files)
    
    # .bedrock_agentcore.yaml
    files.append(BASE_DIR / ".bedrock_agentcore.yaml")
    
    return files


def main():
    """Main cleanup function"""
    print(f"\n{RED}{'='*70}{RESET}")
    print(f"{RED}FILE CLEANUP - RETURNS/REFUNDS AGENT{RESET}")
    print(f"{RED}{'='*70}{RESET}\n")
    
    # Get list of files
    files_to_delete = get_files_to_delete()
    existing_files = [f for f in files_to_delete if f.exists()]
    
    if not existing_files:
        print(f"{YELLOW}No files found to delete.{RESET}")
        return
    
    print(f"{YELLOW}This will delete the following types of files:{RESET}")
    print(f"  • Python scripts (01-25) in scripts/")
    print(f"  • Config JSON files (runtime, gateway, memory, lambda, cognito, etc.)")
    print(f"  • Docker files (Dockerfile, .dockerignore)")
    print(f"  • Requirements files (requirements.txt, requirements_streamlit.txt)")
    print(f"  • Generated agent files (*_agent.py)")
    print(f"  • .bedrock_agentcore.yaml")
    
    print(f"\n{BLUE}Found {len(existing_files)} file(s) to delete{RESET}")
    
    print(f"\n{RED}⚠️  WARNING: This action cannot be undone!{RESET}")
    print(f"{YELLOW}You have 5 seconds to cancel (Ctrl+C)...{RESET}\n")
    
    try:
        for i in range(5, 0, -1):
            print(f"{i}...", end=" ", flush=True)
            time.sleep(1)
        print("\n")
    except KeyboardInterrupt:
        print(f"\n\n{GREEN}Cleanup cancelled by user{RESET}")
        return
    
    print(f"{BLUE}Starting file cleanup...{RESET}\n")
    
    # Delete files by category
    deleted_count = 0
    
    print(f"{BLUE}Deleting Python scripts...{RESET}")
    for i in range(1, 26):
        script_pattern = f"{i:02d}_*.py"
        matching_files = list(SCRIPTS_DIR.glob(script_pattern))
        for script_file in matching_files:
            if safe_delete_file(script_file):
                deleted_count += 1
    
    print(f"\n{BLUE}Deleting config JSON files...{RESET}")
    config_files = [
        "runtime_config.json",
        "gateway_config.json",
        "memory_config.json",
        "lambda_config.json",
        "cognito_config.json",
        "runtime_execution_role_config.json",
        "gateway_role_config.json",
        "kb_config.json"
    ]
    for config_file in config_files:
        if safe_delete_file(BASE_DIR / config_file):
            deleted_count += 1
    
    print(f"\n{BLUE}Deleting Docker files...{RESET}")
    docker_files = ["Dockerfile", ".dockerignore"]
    for docker_file in docker_files:
        if safe_delete_file(BASE_DIR / docker_file):
            deleted_count += 1
    
    print(f"\n{BLUE}Deleting requirements files...{RESET}")
    requirements_files = ["requirements.txt", "requirements_streamlit.txt"]
    for req_file in requirements_files:
        if safe_delete_file(BASE_DIR / req_file):
            deleted_count += 1
    
    print(f"\n{BLUE}Deleting generated agent files...{RESET}")
    agent_files = list((BASE_DIR / "src" / "agents").glob("*_agent.py"))
    for agent_file in agent_files:
        if safe_delete_file(agent_file):
            deleted_count += 1
    
    print(f"\n{BLUE}Deleting .bedrock_agentcore.yaml...{RESET}")
    if safe_delete_file(BASE_DIR / ".bedrock_agentcore.yaml"):
        deleted_count += 1
    
    print(f"\n{GREEN}{'='*70}{RESET}")
    print(f"{GREEN}File cleanup complete!{RESET}")
    print(f"{GREEN}Deleted {deleted_count} file(s){RESET}")
    print(f"{GREEN}{'='*70}{RESET}\n")
    
    print(f"{YELLOW}Note: Documentation and source code have been preserved.{RESET}")
    print(f"{YELLOW}The following remain intact:{RESET}")
    print(f"  • Documentation (docs/, specs/, README.md)")
    print(f"  • Source code (src/agents/policy_engine.py, decision_logger.py)")
    print(f"  • Tests (tests/)")
    print(f"  • Policies (policies/)")
    print(f"  • Infrastructure scripts (infrastructure/)")
    print(f"  • Patches (patches/)\n")


if __name__ == "__main__":
    main()
