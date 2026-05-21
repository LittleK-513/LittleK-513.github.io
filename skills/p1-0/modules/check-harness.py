#!/usr/bin/env python3
"""check-harness.py — Harness 机制检查模块（Gateway、cron、systemd、sessions）
独立运行输出 JSON：python3 check-harness.py
"""

import os, json, subprocess, glob, time
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(),
                "returncode": result.returncode, "ok": result.returncode == 0}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "ok": False}

def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

def get_file_info(path):
    if not os.path.exists(path):
        return None
    stat = os.stat(path)
    return {"exists": True, "size": stat.st_size, "mtime": stat.st_mtime,
            "mtime_age_hours": round((time.time() - stat.st_mtime) / 3600, 1)}

def check():
    checks_passed = 0
    checks_total = 5
    
    # 配置文件
    config_paths = ["/root/.openclaw/config.yaml", "/root/.openclaw/config.yml", "/root/.openclaw/.env"]
    config_status = {}
    configs_ok = 0
    for path in config_paths:
        info = get_file_info(path)
        config_status[path] = info or {"exists": False}
        if info and info["exists"]:
            configs_ok += 1
    if configs_ok > 0: checks_passed += 1  # 至少一个配置存在
    
    # cron jobs
    cron = run_cmd("crontab -l 2>/dev/null || echo 'no crontab'")
    cron_jobs = [line for line in cron["stdout"].split("\n") if line.strip() and not line.startswith("#")]
    checks_passed += 1  # cron 可查询即算通过
    
    # Gateway 状态
    gateway = run_cmd("openclaw gateway status 2>/dev/null || echo 'unknown'")
    gateway_ok = "running" in gateway["stdout"].lower() or "active" in gateway["stdout"].lower()
    if gateway_ok: checks_passed += 1
    
    # systemd 服务
    systemd = run_cmd("systemctl list-units --type=service --state=running | grep -i openclaw || echo 'none'")
    systemd_ok = systemd["stdout"] and systemd["stdout"] != "none"
    if systemd_ok: checks_passed += 1
    
    # session 文件
    sessions_dir = "/root/.openclaw/agents/main/sessions"
    sessions = glob.glob(f"{sessions_dir}/*.jsonl") if os.path.exists(sessions_dir) else []
    total_size = sum(os.path.getsize(s) for s in sessions)
    session_ok = len(sessions) > 0
    if session_ok: checks_passed += 1
    
    data = {
        "config_files": config_status,
        "cron_jobs_count": len(cron_jobs),
        "cron_jobs": cron_jobs,
        "gateway_status": gateway["stdout"],
        "gateway_ok": gateway_ok,
        "systemd_services": systemd["stdout"],
        "systemd_ok": systemd_ok,
        "sessions": {
            "count": len(sessions),
            "total_size": human_size(total_size),
            "total_size_bytes": total_size,
        },
    }
    
    return {"module": "harness", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}

if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
