#!/usr/bin/env python3
"""check-model.py — 模型与运行时信息检查模块
独立运行输出 JSON：python3 check-model.py
"""

import os, sys, json, subprocess
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(),
                "returncode": result.returncode, "ok": result.returncode == 0}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "ok": False}

def check():
    checks_passed = 0
    checks_total = 4
    
    model = os.environ.get("OPENCLAW_MODEL", "unknown")
    agent = os.environ.get("OPENCLAW_AGENT", "unknown")
    session_file = os.environ.get("OPENCLAW_SESSION_FILE", "")
    
    # 运行时检查
    node = run_cmd("node --version")
    python = run_cmd("python3 --version")
    
    # 验证基本检查
    if model != "unknown": checks_passed += 1
    if node["ok"]: checks_passed += 1
    if python["ok"]: checks_passed += 1
    if os.path.isdir(WORKSPACE): checks_passed += 1
    
    data = {
        "model": model,
        "agent": agent,
        "session_file": session_file,
        "python_path": sys.executable,
        "python_version": python["stdout"] if python["ok"] else "unknown",
        "node_version": node["stdout"] if node["ok"] else "unknown",
        "working_dir": WORKSPACE,
        "hostname": run_cmd("hostname")["stdout"] or "unknown",
        "timestamp": datetime.now().isoformat(),
    }
    
    return {"module": "model", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}

if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
