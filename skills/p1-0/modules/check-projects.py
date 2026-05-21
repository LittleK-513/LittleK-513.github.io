#!/usr/bin/env python3
"""check-projects.py — 项目审计模块（workspace + projects/ 扫描）
独立运行输出 JSON：python3 check-projects.py
"""

import os, json, time
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"

EXCLUDE_DIRS = {
    "node_modules", "tmp", ".local", "_layouts", "blog", "downloads", "__pycache__",
    "_posts", "backups", "daily", "data", "diary", "memorized_diary", "memorized_media",
    "memory", "references", "scripts", "skills", "todo", "weekly",
}

EXCLUDE_FILES = {
    ".git", ".github", ".openclaw", ".config", ".cache", ".npm", ".nvm",
}

def check():
    checks_passed = 0
    checks_total = 2
    
    projects = []
    seen = set()
    
    candidates = []
    for item in os.listdir(WORKSPACE):
        item_path = os.path.join(WORKSPACE, item)
        if not os.path.isdir(item_path):
            continue
        if item.startswith(".") or item in EXCLUDE_DIRS or item in EXCLUDE_FILES:
            continue
        candidates.append((item, item_path))
    
    projects_dir = f"{WORKSPACE}/projects"
    if os.path.exists(projects_dir):
        for sub in os.listdir(projects_dir):
            sub_path = os.path.join(projects_dir, sub)
            if os.path.isdir(sub_path) and not sub.startswith(".") and sub not in EXCLUDE_DIRS:
                candidates.append((sub, sub_path))
    
    for name, path in candidates:
        if name in seen:
            continue
        seen.add(name)
        
        has_state = os.path.exists(f"{path}/state.json")
        has_readme = os.path.exists(f"{path}/README.md") or os.path.exists(f"{path}/readme.md")
        has_project_py = os.path.exists(f"{path}/project-status.py")
        has_todo = os.path.exists(f"{path}/todo") and os.path.isdir(f"{path}/todo")
        is_tiered = name.startswith(("p0-", "p1-", "p2-", "p3-"))
        
        try:
            files = os.listdir(path)
            is_empty = len(files) == 0
            only_hidden = all(f.startswith(".") for f in files)
        except:
            continue
        
        is_project = has_state or has_project_py or (has_readme and has_todo) or is_tiered
        if is_empty or only_hidden or not is_project:
            continue
        
        state_info = None
        tier = None
        last_updated = None
        blocker = None
        last_action = None
        
        if has_state:
            try:
                with open(f"{path}/state.json", "r") as f:
                    state_info = json.load(f)
                tier = state_info.get("tier") or state_info.get("p0_id") or state_info.get("tier_id")
                if tier == "github-money":
                    tier = "P0"
                last_updated = (state_info.get("last_updated") or state_info.get("updated_at") or
                               state_info.get("last_update") or state_info.get("scan_time") or
                               state_info.get("completed_at") or state_info.get("started_at"))
                blocker = state_info.get("blocker") or state_info.get("current_blocker")
                last_action = (state_info.get("last_action") or state_info.get("latest_progress") or
                              state_info.get("last_action_summary") or state_info.get("current_phase"))
            except:
                state_info = {"error": "invalid json"}
        
        file_count = 0
        latest_mtime = 0
        for root, dirs, files_inner in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "__pycache__", ".git"]]
            file_count += len(files_inner)
            for f in files_inner:
                try:
                    mtime = os.path.getmtime(os.path.join(root, f))
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                except:
                    pass
        
        age_hours = (time.time() - latest_mtime) / 3600 if latest_mtime else float("inf")
        
        check_time = last_updated
        if not check_time and latest_mtime:
            check_time = datetime.fromtimestamp(latest_mtime).isoformat()
        
        if file_count == 0:
            status = "ghost"
        elif has_state and check_time:
            try:
                lu_dt = datetime.fromisoformat(check_time.replace("Z", "+00:00"))
                lu_age = (datetime.now() - lu_dt).total_seconds() / 3600
                status = "active" if lu_age < 168 else "stale"
            except:
                status = "stale"
        elif has_state and not check_time:
            status = "stale"
        elif file_count > 0:
            status = "orphan"
        else:
            status = "ghost"
        
        projects.append({
            "name": name,
            "path": path,
            "has_state_json": has_state,
            "has_readme": has_readme,
            "has_project_py": has_project_py,
            "has_todo": has_todo,
            "file_count": file_count,
            "last_modified": datetime.fromtimestamp(latest_mtime).isoformat() if latest_mtime else None,
            "age_hours": round(age_hours, 1),
            "status": status,
            "tier": tier,
            "blocker": blocker,
            "last_action": str(last_action)[:200] if last_action else None,
        })
    
    tier_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    projects.sort(key=lambda x: (tier_order.get(x["tier"], 99), x["name"]))
    
    active_count = len([p for p in projects if p["status"] == "active"])
    if active_count >= 1: checks_passed += 1
    if len(projects) >= 1: checks_passed += 1
    
    data = {
        "projects": projects,
        "active_count": active_count,
        "stale_count": len([p for p in projects if p["status"] == "stale"]),
        "orphan_count": len([p for p in projects if p["status"] == "orphan"]),
        "ghost_count": len([p for p in projects if p["status"] == "ghost"]),
        "total_count": len(projects),
    }
    
    return {"module": "projects", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}

if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
