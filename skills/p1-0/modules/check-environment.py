#!/usr/bin/env python3
"""check-environment.py — 运行环境检查模块（磁盘、内存、负载、Git）
独立运行输出 JSON：python3 check-environment.py
"""

import os, json, subprocess, time
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
    
    # 磁盘
    df = run_cmd("df -h . | tail -1")
    disk_match = df["stdout"].split() if df["ok"] else []
    disk_pct = int(disk_match[4].rstrip("%")) if len(disk_match) >= 5 else 0
    disk_ok = disk_pct < 90
    if disk_ok: checks_passed += 1
    
    # 内存
    free = run_cmd("free -h | grep Mem")
    mem_ok = free["ok"]
    if mem_ok: checks_passed += 1
    
    # 负载/运行时间
    uptime = run_cmd("uptime")
    uptime_ok = uptime["ok"]
    if uptime_ok: checks_passed += 1
    
    # Git
    branch = run_cmd("git branch --show-current")
    status = run_cmd("git status --short")
    last_commit = run_cmd("git log -1 --format=%H")
    last_commit_time = run_cmd("git log -1 --format=%ci")
    commit_count = run_cmd("git rev-list --count HEAD")
    
    git_ok = branch["ok"]
    if git_ok: checks_passed += 1
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "hostname": run_cmd("hostname")["stdout"] or "unknown",
        "uptime": uptime["stdout"] if uptime["ok"] else "unknown",
        "disk": {
            "usage_percent": disk_pct,
            "available": disk_match[3] if len(disk_match) >= 4 else "unknown",
            "raw": df["stdout"] if df["ok"] else "unknown",
            "ok": disk_ok,
        },
        "memory": {
            "raw": free["stdout"] if free["ok"] else "unknown",
            "ok": mem_ok,
        },
        "git": {
            "branch": branch["stdout"] if branch["ok"] else "unknown",
            "uncommitted_changes": status["stdout"].split("\n") if status["stdout"] else [],
            "has_uncommitted": len(status["stdout"]) > 0 if status["ok"] else False,
            "last_commit_hash": last_commit["stdout"][:8] if last_commit["ok"] else "unknown",
            "last_commit_time": last_commit_time["stdout"] if last_commit_time["ok"] else "unknown",
            "total_commits": int(commit_count["stdout"]) if commit_count["ok"] else 0,
            "ok": git_ok,
        },
        "versions": {
            "node": run_cmd("node --version")["stdout"] or "unknown",
            "python": run_cmd("python3 --version")["stdout"] or "unknown",
            "gh_cli": run_cmd("gh --version | head -1")["stdout"] or "unknown",
            "openclaw": run_cmd("openclaw --version 2>/dev/null || openclaw version 2>/dev/null || echo 'unknown'")["stdout"] or "unknown",
        },
    }
    
    return {"module": "environment", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}

if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
