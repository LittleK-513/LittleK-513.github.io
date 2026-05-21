#!/usr/bin/env python3
"""check-memory.py — 记忆系统检查模块（关键文件、日记活跃度）
独立运行输出 JSON：python3 check-memory.py
"""

import os, json, glob, time
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"

def get_file_info(path):
    if not os.path.exists(path):
        return None
    stat = os.stat(path)
    return {"exists": True, "size": stat.st_size, "size_human": human_size(stat.st_size),
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "mtime_age_hours": round((time.time() - stat.st_mtime) / 3600, 1)}

def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

def check():
    checks_passed = 0
    checks_total = 3
    
    memory_dir = f"{WORKSPACE}/memory"
    diary_dir = f"{WORKSPACE}/diary"
    
    memory_files = glob.glob(f"{memory_dir}/**/*.md", recursive=True)
    diary_files = glob.glob(f"{diary_dir}/*.md")
    
    # 关键文件
    key_files = {
        "MEMORY.md": f"{WORKSPACE}/MEMORY.md",
        "USER.md": f"{WORKSPACE}/USER.md",
        "SOUL.md": f"{WORKSPACE}/SOUL.md",
        "IDENTITY.md": f"{WORKSPACE}/IDENTITY.md",
        "AGENTS.md": f"{WORKSPACE}/AGENTS.md",
        "BOOTSTRAP.md": f"{WORKSPACE}/BOOTSTRAP.md",
        "HEARTBEAT.md": f"{WORKSPACE}/HEARTBEAT.md",
    }
    
    key_status = {}
    all_exist = True
    for name, path in key_files.items():
        info = get_file_info(path)
        key_status[name] = info or {"exists": False}
        if not (info and info["exists"]):
            all_exist = False
    
    if all_exist: checks_passed += 1
    if len(memory_files) >= 5: checks_passed += 1
    
    # 日记活跃度
    now = time.time()
    recent_diary = []
    for f in diary_files:
        stat = os.stat(f)
        age_hours = (now - stat.st_mtime) / 3600
        if age_hours < 168:  # 7 days
            recent_diary.append({"file": os.path.basename(f), "age_hours": round(age_hours, 1)})
    recent_diary.sort(key=lambda x: x["age_hours"])
    
    if len(recent_diary) >= 3: checks_passed += 1
    
    data = {
        "key_files": key_status,
        "all_key_files_exist": all_exist,
        "memory_files_count": len(memory_files),
        "diary_total_count": len(diary_files),
        "diary_recent_7d": len(recent_diary),
        "diary_latest": recent_diary[:5] if recent_diary else None,
    }
    
    return {"module": "memory", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}

if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
