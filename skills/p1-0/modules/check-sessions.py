#!/usr/bin/env python3
"""check-sessions.py — 会话历史检查模块（最近 session 文件）
独立运行输出 JSON：python3 check-sessions.py
"""

import os, json, glob, time
from datetime import datetime

SESSIONS_DIR = "/root/.openclaw/agents/main/sessions"

def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

def check():
    checks_passed = 0
    checks_total = 2
    
    if not os.path.exists(SESSIONS_DIR):
        return {
            "module": "sessions",
            "data": {"error": "sessions dir not found", "total_sessions": 0, "recent_10": []},
            "checks_passed": 0,
            "checks_total": 2,
        }
    
    sessions = sorted(glob.glob(f"{SESSIONS_DIR}/*.jsonl"), key=lambda x: os.path.getmtime(x), reverse=True)
    
    if len(sessions) > 0: checks_passed += 1
    
    recent = sessions[:10]
    session_summaries = []
    for s in recent:
        stat = os.stat(s)
        size = stat.st_size
        mtime = stat.st_mtime
        
        first_line = None
        if size > 0:
            try:
                with open(s, "r", errors="ignore") as f:
                    first_line = f.readline().strip()
            except:
                pass
        
        session_summaries.append({
            "file": os.path.basename(s),
            "size": human_size(size),
            "mtime": datetime.fromtimestamp(mtime).isoformat(),
            "age_hours": round((time.time() - mtime) / 3600, 1),
            "first_line": first_line[:200] if first_line else None,
        })
    
    if len(session_summaries) >= 5: checks_passed += 1
    
    data = {
        "total_sessions": len(sessions),
        "recent_10": session_summaries,
    }
    
    return {"module": "sessions", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}

if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
