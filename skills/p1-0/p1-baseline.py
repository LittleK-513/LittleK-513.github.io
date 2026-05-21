#!/usr/bin/env python3
"""
p1-baseline.py — P1.0 全面状态检查系统
全面检查：模型、Harness机制、记忆机制、项目机制、运行环境、能力
输出：JSON 数据包 + Markdown 报告 + HTML 可视化
"""

import os
import sys
import json
import time
import subprocess
import glob
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = "/root/.openclaw/workspace"
OUTPUT_DIR = f"{WORKSPACE}/skills/p1-0/reports"
SKILL_DIR = f"{WORKSPACE}/skills/p1-0"
REPORTS_DIR = f"{WORKSPACE}/reports/p1-0"

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(f"{REPORTS_DIR}/history", exist_ok=True)

def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
            "ok": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "timeout", "returncode": -1, "ok": False}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "ok": False}

def get_file_info(path):
    """获取文件信息"""
    if not os.path.exists(path):
        return None
    stat = os.stat(path)
    return {
        "exists": True,
        "size": stat.st_size,
        "size_human": human_size(stat.st_size),
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "mtime_age_hours": round((time.time() - stat.st_mtime) / 3600, 1),
    }

def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

def get_git_info():
    """检查 git 状态"""
    branch = run_cmd("git branch --show-current")
    status = run_cmd("git status --short")
    last_commit = run_cmd("git log -1 --format=%H")
    last_commit_time = run_cmd("git log -1 --format=%ci")
    commit_count = run_cmd("git rev-list --count HEAD")
    
    return {
        "branch": branch["stdout"] if branch["ok"] else "unknown",
        "uncommitted_changes": status["stdout"].split("\n") if status["stdout"] else [],
        "has_uncommitted": len(status["stdout"]) > 0 if status["ok"] else False,
        "last_commit_hash": last_commit["stdout"][:8] if last_commit["ok"] else "unknown",
        "last_commit_time": last_commit_time["stdout"] if last_commit_time["ok"] else "unknown",
        "total_commits": int(commit_count["stdout"]) if commit_count["ok"] else 0,
    }

def get_system_info():
    """系统环境检查"""
    df = run_cmd("df -h . | tail -1")
    free = run_cmd("free -h | grep Mem")
    uptime = run_cmd("uptime")
    node = run_cmd("node --version")
    python = run_cmd("python3 --version")
    gh = run_cmd("gh --version | head -1")
    openclaw = run_cmd("openclaw --version 2>/dev/null || openclaw version 2>/dev/null || echo 'unknown'")
    
    disk_match = df["stdout"].split() if df["ok"] else []
    
    return {
        "timestamp": datetime.now().isoformat(),
        "hostname": run_cmd("hostname")["stdout"],
        "uptime": uptime["stdout"] if uptime["ok"] else "unknown",
        "disk": {
            "usage_percent": int(disk_match[4].rstrip("%")) if len(disk_match) >= 5 else 0,
            "available": disk_match[3] if len(disk_match) >= 4 else "unknown",
            "raw": df["stdout"],
        },
        "memory": {
            "raw": free["stdout"] if free["ok"] else "unknown",
        },
        "versions": {
            "node": node["stdout"] if node["ok"] else "unknown",
            "python": python["stdout"] if python["ok"] else "unknown",
            "gh_cli": gh["stdout"] if gh["ok"] else "unknown",
            "openclaw": openclaw["stdout"] if openclaw["ok"] else "unknown",
        },
    }

def get_memory_system():
    """记忆系统全面审计"""
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
    
    # 日记活跃度
    recent_diary = []
    now = time.time()
    for f in diary_files:
        stat = os.stat(f)
        age_hours = (now - stat.st_mtime) / 3600
        if age_hours < 168:  # 7 days
            recent_diary.append({
                "file": os.path.basename(f),
                "age_hours": round(age_hours, 1),
            })
    
    recent_diary.sort(key=lambda x: x["age_hours"])
    
    return {
        "key_files": key_status,
        "all_key_files_exist": all_exist,
        "memory_files_count": len(memory_files),
        "diary_total_count": len(diary_files),
        "diary_recent_7d": len(recent_diary),
        "diary_latest": recent_diary[:5] if recent_diary else None,
    }

def get_harness_mechanisms():
    """Harness 机制检查 — OpenClaw/Gateway 配置"""
    
    # 检查 OpenClaw 配置
    config_paths = [
        "/root/.openclaw/config.yaml",
        "/root/.openclaw/config.yml",
        "/root/.openclaw/.env",
    ]
    
    config_status = {}
    for path in config_paths:
        config_status[path] = get_file_info(path)
    
    # 检查 cron jobs
    cron = run_cmd("crontab -l 2>/dev/null || echo 'no crontab'")
    cron_jobs = [line for line in cron["stdout"].split("\n") if line.strip() and not line.startswith("#")]
    
    # 检查 Gateway 状态
    gateway = run_cmd("openclaw gateway status 2>/dev/null || echo 'unknown'")
    
    # 检查 systemd 服务
    systemd = run_cmd("systemctl list-units --type=service --state=running | grep -i openclaw || echo 'none'")
    
    # 检查 session 文件
    sessions_dir = "/root/.openclaw/agents/main/sessions"
    sessions = glob.glob(f"{sessions_dir}/*.jsonl") if os.path.exists(sessions_dir) else []
    
    total_session_size = 0
    for s in sessions:
        total_session_size += os.path.getsize(s)
    
    return {
        "config_files": config_status,
        "cron_jobs_count": len(cron_jobs),
        "cron_jobs": cron_jobs,
        "gateway_status": gateway["stdout"],
        "systemd_services": systemd["stdout"],
        "sessions": {
            "count": len(sessions),
            "total_size": human_size(total_session_size),
            "total_size_bytes": total_session_size,
        },
    }

def get_projects():
    """项目全面审计 — 支持多种目录结构"""
    projects = []
    seen = set()
    
    # 策略1: 扫描 workspace 一级目录
    candidates = []
    for item in os.listdir(WORKSPACE):
        item_path = os.path.join(WORKSPACE, item)
        if not os.path.isdir(item_path):
            continue
        if item.startswith(".") or item in ["node_modules", "tmp", ".local", "_layouts", "blog", "downloads", "__pycache__", "_posts", "backups", "daily", "data", "diary", "memorized_diary", "memorized_media", "memory", "references", "scripts", "skills", "todo", "weekly", "bounty_archive.md", "data.json", "data.jsonl", "index.html", "index.html.bak", "CNAME", "_config.yml", "founders-handbook.md", "capability-inventory.md", "claude-openclaw-bridge.md", "mac-bridge-websocket-spec.md", "mac-forward-message.json", "ac_api.py", "AGENTS.md", "BOOTSTRAP.md", "DREAMS.md", "EOF", "HEARTBEAT.md", "IDENTITY.md", "MEMORY.md", "SOUL.md", "USER.md", "TOOLS.md", "1", "@", "d22_test.txt", "littlek-513.github.io", "p1-dashboard.html", "qq-test-session.jsonl", "qq-test-session.txt", "weixin_health.sh", "weixin-msg-payload.json", "README.md", "readme.md", "package.json", "package-lock.json"]:
            continue
        candidates.append((item, item_path))
    
    # 策略2: 特别检查 projects/ 下的子目录
    projects_dir = f"{WORKSPACE}/projects"
    if os.path.exists(projects_dir):
        for sub in os.listdir(projects_dir):
            sub_path = os.path.join(projects_dir, sub)
            if os.path.isdir(sub_path) and not sub.startswith("."):
                candidates.append((sub, sub_path))
    
    for name, path in candidates:
        if name in seen:
            continue
        seen.add(name)
        
        # 判断是否为项目 — 严格的判定标准
        has_state = os.path.exists(f"{path}/state.json")
        has_readme = os.path.exists(f"{path}/README.md") or os.path.exists(f"{path}/readme.md")
        has_project_py = os.path.exists(f"{path}/project-status.py")
        has_todo = os.path.exists(f"{path}/todo") and os.path.isdir(f"{path}/todo")
        is_tiered = name.startswith(("p0-", "p1-", "p2-", "p3-"))
        
        # 排除标准
        is_empty = len(os.listdir(path)) == 0
        only_hidden = all(f.startswith(".") for f in os.listdir(path))
        
        # 严格判定：满足以下任一条件
        is_project = has_state or has_project_py or (has_readme and has_todo) or is_tiered
        
        if is_empty or only_hidden or not is_project:
            continue
        
        # 读取 state.json（支持多种格式）
        state_info = None
        tier = None
        last_updated = None
        blocker = None
        last_action = None
        
        if has_state:
            try:
                with open(f"{path}/state.json", "r") as f:
                    state_info = json.load(f)
                
                # 灵活提取字段（支持多种命名）
                tier = state_info.get("tier") or state_info.get("p0_id") or state_info.get("tier_id")
                if tier == "github-money":
                    tier = "P0"
                
                last_updated = (state_info.get("last_updated") or 
                               state_info.get("updated_at") or 
                               state_info.get("last_update") or
                               state_info.get("scan_time") or
                               state_info.get("completed_at") or
                               state_info.get("started_at"))
                blocker = state_info.get("blocker") or state_info.get("current_blocker")
                last_action = (state_info.get("last_action") or 
                              state_info.get("latest_progress") or 
                              state_info.get("last_action_summary") or
                              state_info.get("current_phase"))
            except:
                state_info = {"error": "invalid json"}
        
        # 统计文件
        file_count = 0
        latest_mtime = 0
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "__pycache__", ".git"]]
            file_count += len(files)
            for f in files:
                try:
                    mtime = os.path.getmtime(os.path.join(root, f))
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                except:
                    pass
        
        age_hours = (time.time() - latest_mtime) / 3600 if latest_mtime else float("inf")
        
        # 状态判定 — 优先用 last_updated，如无则用文件修改时间
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
    
    # 按 tier 排序（P0 > P1 > P2 > other）
    tier_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    projects.sort(key=lambda x: (tier_order.get(x["tier"], 99), x["name"]))
    
    return projects

def get_capabilities():
    """能力验证 — 外部连接检查"""
    
    # GitHub
    gh_auth = run_cmd("gh auth status 2>&1 | head -5")
    gh_ok = "Logged in" in gh_auth["stdout"] or gh_auth["ok"]
    
    # GitHub API 测试
    gh_api = run_cmd("gh api user 2>&1 | head -1")
    gh_api_ok = gh_api["ok"] and "login" in gh_api["stdout"]
    
    # Web 搜索测试（轻量）
    search_ok = True  # 依赖 kimi_search tool，无法直接测试
    
    # 飞书 token
    feishu_ok = os.path.exists("/root/.openclaw/.feishu_token") or os.path.exists(f"{WORKSPACE}/.feishu_token")
    
    # Cloudflare Tunnel
    tunnel = run_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:8080 2>/dev/null || echo '000'")
    tunnel_ok = tunnel["stdout"] in ["200", "404", "301", "302"]
    
    # 邮件 webhook
    mailgun = run_cmd("systemctl is-active xiaok-mailbox-webhook 2>/dev/null || echo 'inactive'")
    mailgun_ok = "active" in mailgun["stdout"]
    
    return {
        "github_cli": gh_ok,
        "github_api": gh_api_ok,
        "web_search": search_ok,
        "feishu": feishu_ok,
        "cloudflare_tunnel": tunnel_ok,
        "mailgun_webhook": mailgun_ok,
        "raw": {
            "gh_auth": gh_auth["stdout"],
            "gh_api": gh_api["stdout"],
            "tunnel_http_code": tunnel["stdout"],
            "mailgun": mailgun["stdout"],
        },
    }

def get_session_history_summary():
    """从历史会话提取项目进展"""
    sessions_dir = "/root/.openclaw/agents/main/sessions"
    
    if not os.path.exists(sessions_dir):
        return {"error": "sessions dir not found"}
    
    sessions = sorted(
        glob.glob(f"{sessions_dir}/*.jsonl"),
        key=lambda x: os.path.getmtime(x),
        reverse=True
    )
    
    # 取最近 10 个 session
    recent = sessions[:10]
    
    session_summaries = []
    for s in recent:
        stat = os.stat(s)
        size = stat.st_size
        mtime = stat.st_mtime
        
        # 读取第一行获取 session 信息
        first_line = None
        if size > 0:
            with open(s, "r", errors="ignore") as f:
                first_line = f.readline().strip()
        
        session_summaries.append({
            "file": os.path.basename(s),
            "size": human_size(size),
            "mtime": datetime.fromtimestamp(mtime).isoformat(),
            "age_hours": round((time.time() - mtime) / 3600, 1),
            "first_line": first_line[:200] if first_line else None,
        })
    
    return {
        "total_sessions": len(sessions),
        "recent_10": session_summaries,
    }

def get_model_info():
    """当前模型和运行时信息"""
    # 从 OpenClaw 环境获取
    model = os.environ.get("OPENCLAW_MODEL", "unknown")
    agent = os.environ.get("OPENCLAW_AGENT", "unknown")
    
    # 读取 session status
    session_file = os.environ.get("OPENCLAW_SESSION_FILE", "")
    
    return {
        "model": model,
        "agent": agent,
        "session_file": session_file,
        "python_path": sys.executable,
        "working_dir": WORKSPACE,
    }

def calculate_score(data):
    """计算系统健康分"""
    score = 0
    breakdown = {}
    
    # 项目健康 (30%)
    projects = data.get("projects", [])
    active = len([p for p in projects if p["status"] == "active"])
    total = len(projects)
    if total > 0:
        project_score = min(10, (active / total) * 10)
    else:
        project_score = 5
    breakdown["projects"] = round(project_score, 1)
    score += project_score * 0.30
    
    # 环境稳定 (20%)
    env = data.get("environment", {})
    disk = env.get("disk", {}).get("usage_percent", 0)
    env_score = 10 if disk < 80 else (5 if disk < 90 else 0)
    breakdown["environment"] = env_score
    score += env_score * 0.20
    
    # 记忆完整 (20%)
    memory = data.get("memory_system", {})
    mem_score = 10 if memory.get("all_key_files_exist") else 5
    if memory.get("diary_recent_7d", 0) < 3:
        mem_score -= 2
    breakdown["memory"] = max(0, mem_score)
    score += max(0, mem_score) * 0.20
    
    # 能力可用 (20%)
    cap = data.get("capabilities", {})
    cap_list = [cap.get("github_cli"), cap.get("github_api"), cap.get("feishu"), cap.get("cloudflare_tunnel")]
    available = sum(1 for c in cap_list if c)
    cap_score = (available / len(cap_list)) * 10 if cap_list else 5
    breakdown["capabilities"] = round(cap_score, 1)
    score += cap_score * 0.20
    
    # 历史趋势 (10%)
    trend_score = 5  # 默认持平
    breakdown["trend"] = trend_score
    score += trend_score * 0.10
    
    return round(score, 1), breakdown

def generate_alerts(data):
    """生成告警清单"""
    alerts = []
    
    # 项目告警
    for p in data.get("projects", []):
        if p["status"] == "stale":
            alerts.append({
                "level": "warning",
                "category": "project",
                "item": f"{p['name']} stale {p['age_hours']:.0f}h",
                "suggestion": f"检查 {p['name']} 的 blocker 或推进 next action",
            })
        elif p["status"] == "ghost":
            alerts.append({
                "level": "info",
                "category": "project",
                "item": f"{p['name']} 是 ghost 项目",
                "suggestion": "归档或填充内容",
            })
    
    # 环境告警
    env = data.get("environment", {})
    disk_pct = env.get("disk", {}).get("usage_percent", 0)
    if disk_pct > 85:
        alerts.append({
            "level": "critical",
            "category": "environment",
            "item": f"磁盘使用率 {disk_pct}%",
            "suggestion": "清理日志和旧 session 文件",
        })
    
    # 记忆告警
    mem = data.get("memory_system", {})
    if not mem.get("all_key_files_exist"):
        missing = [k for k, v in mem.get("key_files", {}).items() if not v or not v.get("exists")]
        alerts.append({
            "level": "critical",
            "category": "memory",
            "item": f"关键文件缺失: {', '.join(missing)}",
            "suggestion": "从 git 恢复或重建文件",
        })
    
    if mem.get("diary_recent_7d", 0) == 0:
        alerts.append({
            "level": "warning",
            "category": "memory",
            "item": "7 天内无日记记录",
            "suggestion": "检查内观机制是否正常运行",
        })
    
    # 能力告警
    cap = data.get("capabilities", {})
    if not cap.get("github_api"):
        alerts.append({
            "level": "warning",
            "category": "capability",
            "item": "GitHub API 不可用",
            "suggestion": "检查 PAT 是否过期",
        })
    
    # 排序
    level_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: level_order.get(x["level"], 99))
    
    return alerts

def generate_json_report(data):
    """生成完整 JSON 报告"""
    score, breakdown = calculate_score(data)
    alerts = generate_alerts(data)
    
    report = {
        "meta": {
            "version": "p1-baseline-v2",
            "generated_at": datetime.now().isoformat(),
            "workspace": WORKSPACE,
        },
        "score": {
            "total": score,
            "max": 10,
            "breakdown": breakdown,
            "grade": "A" if score >= 8 else ("B" if score >= 6 else ("C" if score >= 4 else "D")),
        },
        "model": data.get("model", {}),
        "environment": data.get("environment", {}),
        "harness": data.get("harness", {}),
        "memory_system": data.get("memory_system", {}),
        "projects": data.get("projects", []),
        "capabilities": data.get("capabilities", {}),
        "session_history": data.get("session_history", {}),
        "git": data.get("git", {}),
        "alerts": alerts,
        "alert_count": {
            "critical": len([a for a in alerts if a["level"] == "critical"]),
            "warning": len([a for a in alerts if a["level"] == "warning"]),
            "info": len([a for a in alerts if a["level"] == "info"]),
        },
    }
    
    return report

def generate_markdown_report(report):
    """生成 Markdown 人类可读报告"""
    meta = report["meta"]
    score = report["score"]
    env = report["environment"]
    harness = report["harness"]
    memory = report["memory_system"]
    projects = report["projects"]
    cap = report["capabilities"]
    git = report["git"]
    alerts = report["alerts"]
    
    md = f"""# P1.0 系统状态报告

> 生成时间：{meta['generated_at']}
> 版本：{meta['version']}
> 工作区：{meta['workspace']}

---

## 综合评分：{score['total']}/10（{score['grade']} 级）

| 维度 | 得分 | 权重 | 加权 |
|------|------|------|------|
"""
    for dim, val in score["breakdown"].items():
        weights = {"projects": "30%", "environment": "20%", "memory": "20%", "capabilities": "20%", "trend": "10%"}
        md += f"| {dim} | {val} | {weights.get(dim, '-')} | {round(val * float(weights.get(dim, '0').rstrip('%'))/100, 2)} |\n"
    
    md += f"""
---

## 告警清单

| 级别 | 类别 | 问题 | 建议 |
|------|------|------|------|
"""
    if alerts:
        for a in alerts:
            icon = "🔴" if a["level"] == "critical" else ("🟡" if a["level"] == "warning" else "🟢")
            md += f"| {icon} {a['level']} | {a['category']} | {a['item']} | {a['suggestion']} |\n"
    else:
        md += "| 🟢 | - | 无告警 | 系统运行正常 |\n"
    
    md += f"""
---

## 运行环境

```
主机：{env.get('hostname', 'unknown')}
运行时间：{env.get('uptime', 'unknown')}
磁盘：{env.get('disk', {}).get('raw', 'unknown')}
内存：{env.get('memory', {}).get('raw', 'unknown')}
Node.js：{env.get('versions', {}).get('node', 'unknown')}
Python：{env.get('versions', {}).get('python', 'unknown')}
OpenClaw：{env.get('versions', {}).get('openclaw', 'unknown')}
```

---

## Harness 机制

| 检查项 | 状态 |
|--------|------|
| Cron Jobs | {harness.get('cron_jobs_count', 0)} 条 |
| Gateway | {harness.get('gateway_status', 'unknown')} |
| Sessions | {harness.get('sessions', {}).get('count', 0)} 个文件，共 {harness.get('sessions', {}).get('total_size', '0')} |
| Git 分支 | {git.get('branch', 'unknown')} |
| Git 未提交 | {'有' if git.get('has_uncommitted') else '无'} |
| 上次提交 | {git.get('last_commit_hash', 'unknown')} @ {git.get('last_commit_time', 'unknown')} |

### Cron Jobs

```
"""
    for job in harness.get("cron_jobs", []):
        md += f"{job}\n"
    md += """```

---

## 记忆系统

| 关键文件 | 状态 | 大小 | 最后修改 |
|----------|------|------|----------|
"""
    for name, info in memory.get("key_files", {}).items():
        if info and info.get("exists"):
            md += f"| {name} | ✅ | {info.get('size_human', '-')} | {info.get('mtime', '-')} |\n"
        else:
            md += f"| {name} | ❌ 缺失 | - | - |\n"
    
    md += f"""
**统计**：记忆文件 {memory.get('memory_files_count', 0)} 个，日记 {memory.get('diary_total_count', 0)} 篇（最近7天 {memory.get('diary_recent_7d', 0)} 篇）

---

## 项目审计

| 项目 | Tier | 状态 | 文件数 | 最后活跃 | Blocker | 最近动作 |
|------|------|------|--------|----------|---------|----------|
"""
    for p in projects:
        tier = p.get("tier", "-") or "-"
        status_icon = "🟢" if p["status"] == "active" else ("🟡" if p["status"] == "stale" else "⚪")
        blocker = (p.get("blocker") or "-")[:30]
        action = (p.get("last_action") or "-")[:40]
        md += f"| {p['name']} | {tier} | {status_icon} {p['status']} | {p['file_count']} | {p['age_hours']:.0f}h | {blocker} | {action} |\n"
    
    md += f"""
---

## 能力验证

| 能力 | 状态 |
|------|------|
| GitHub CLI | {'✅' if cap.get('github_cli') else '❌'} |
| GitHub API | {'✅' if cap.get('github_api') else '❌'} |
| Web 搜索 | {'✅' if cap.get('web_search') else '❌'} |
| 飞书 | {'✅' if cap.get('feishu') else '❌'} |
| Cloudflare Tunnel | {'✅' if cap.get('cloudflare_tunnel') else '❌'} |
| 邮件 Webhook | {'✅' if cap.get('mailgun_webhook') else '❌'} |

---

## 会话历史

最近会话：{report.get('session_history', {}).get('total_sessions', 0)} 个文件

"""
    for s in report.get("session_history", {}).get("recent_10", [])[:5]:
        md += f"- `{s['file']}` ({s['size']}, {s['age_hours']:.0f}h ago)\n"
    
    md += """
---

*报告由 p1-baseline.py 自动生成*
"""
    
    return md

def get_skill_source():
    """读取 Skill 文档和脚本源码"""
    sources = {}
    
    # Skill 文档
    doc_path = f"{WORKSPACE}/skills/p1-0/baseline-check-v2.md"
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            sources["doc"] = f.read()
    except Exception:
        sources["doc"] = "# Skill 文档未找到\n"
    
    # 检查脚本
    script_path = f"{WORKSPACE}/skills/p1-0/p1-baseline.py"
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            sources["script"] = f.read()
    except Exception:
        sources["script"] = "# 脚本未找到\n"
    
    return sources

def generate_html_dashboard(report):
    """生成 HTML 可视化仪表板"""
    score = report["score"]
    env = report["environment"]
    harness = report["harness"]
    memory = report["memory_system"]
    projects = report["projects"]
    cap = report["capabilities"]
    alerts = report["alerts"]
    
    # 读取 Skill 源码
    skill_sources = get_skill_source()
    skill_doc_content = skill_sources["doc"].replace("<", "&lt;").replace(">", "&gt;")
    skill_script_content = skill_sources["script"].replace("<", "&lt;").replace(">", "&gt;")
    
    critical = len([a for a in alerts if a["level"] == "critical"])
    warning = len([a for a in alerts if a["level"] == "warning"])
    info = len([a for a in alerts if a["level"] == "info"])
    
    # 项目状态数据（给 JS 用）
    project_data = json.dumps(projects)
    
    # 评分维度数据
    score_data = json.dumps(score["breakdown"])
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>P1.0 系统状态 · 小K</title>
<style>
:root {{
  --bg: #0a0a0f;
  --card: #13131f;
  --card-hover: #1a1a2e;
  --text: #e0e0e0;
  --text-dim: #888;
  --accent: #00d4ff;
  --accent-dim: #0088aa;
  --good: #00ff88;
  --warn: #ffcc00;
  --bad: #ff4444;
  --border: #222;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace;
  line-height: 1.6;
  min-height: 100vh;
}}
.container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
header {{
  text-align: center;
  padding: 3rem 1rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2rem;
}}
header h1 {{
  font-size: 2.5rem;
  font-weight: 300;
  letter-spacing: 2px;
  margin-bottom: 0.5rem;
}}
header .subtitle {{ color: var(--text-dim); font-size: 0.9rem; }}

.score-ring {{
  width: 200px;
  height: 200px;
  margin: 2rem auto;
  position: relative;
}}
.score-ring svg {{
  transform: rotate(-90deg);
}}
.score-ring .score-text {{
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 3rem;
  font-weight: 200;
}}
.score-ring .score-label {{
  position: absolute;
  top: 65%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 1rem;
  color: var(--text-dim);
}}

.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}}
.card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.3s ease;
}}
.card:hover {{ background: var(--card-hover); border-color: var(--accent-dim); }}
.card h2 {{
  font-size: 1rem;
  font-weight: 500;
  color: var(--accent);
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}}

.status-badge {{
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 500;
  margin: 0.2rem;
}}
.badge-good {{ background: rgba(0,255,136,0.15); color: var(--good); border: 1px solid var(--good); }}
.badge-warn {{ background: rgba(255,204,0,0.15); color: var(--warn); border: 1px solid var(--warn); }}
.badge-bad {{ background: rgba(255,68,68,0.15); color: var(--bad); border: 1px solid var(--bad); }}
.badge-info {{ background: rgba(0,212,255,0.15); color: var(--accent); border: 1px solid var(--accent); }}

.alert-item {{
  padding: 0.75rem;
  margin: 0.5rem 0;
  border-radius: 8px;
  border-left: 3px solid;
  background: rgba(255,255,255,0.03);
}}
.alert-critical {{ border-left-color: var(--bad); }}
.alert-warning {{ border-left-color: var(--warn); }}
.alert-info {{ border-left-color: var(--accent); }}

.project-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
}}
.project-row:last-child {{ border-bottom: none; }}
.project-name {{ font-weight: 500; }}
.project-meta {{ color: var(--text-dim); font-size: 0.85rem; }}

.metric {{
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}}
.metric:last-child {{ border-bottom: none; }}
.metric-value {{ font-family: monospace; color: var(--accent); }}

table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}}
th, td {{
  text-align: left;
  padding: 0.6rem;
  border-bottom: 1px solid var(--border);
}}
th {{
  color: var(--accent);
  font-weight: 500;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 1px;
}}
tr:hover {{ background: rgba(255,255,255,0.02); }}

footer {{
  text-align: center;
  padding: 3rem 1rem;
  color: var(--text-dim);
  font-size: 0.8rem;
  border-top: 1px solid var(--border);
  margin-top: 2rem;
}}

.chart-bar {{
  display: flex;
  align-items: center;
  margin: 0.5rem 0;
}}
.chart-label {{
  width: 80px;
  font-size: 0.8rem;
  color: var(--text-dim);
}}
.chart-fill {{
  height: 20px;
  border-radius: 4px;
  background: var(--accent);
  transition: width 0.5s ease;
  position: relative;
}}
.chart-fill::after {{
  content: attr(data-value);
  position: absolute;
  right: -35px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.75rem;
  color: var(--text);
}}

@media (max-width: 600px) {{
  .grid {{ grid-template-columns: 1fr; }}
  header h1 {{ font-size: 1.8rem; }}
}}
</style>
</head>
<body>
<div class="container">

<header>
  <h1>P1.0 系统状态</h1>
  <p class="subtitle">全面检查 · 模型 · Harness · 记忆 · 项目 · 环境 · 能力</p>
  <p class="subtitle">生成于 {report["meta"]["generated_at"][:19]}</p>
</header>

<!-- 评分圆环 -->
<div class="score-ring">
  <svg width="200" height="200" viewBox="0 0 200 200">
    <circle cx="100" cy="100" r="90" fill="none" stroke="#1a1a2e" stroke-width="12"/>
    <circle id="score-circle" cx="100" cy="100" r="90" fill="none" stroke="var(--accent)" stroke-width="12"
      stroke-dasharray="565.5" stroke-dashoffset="{{565.5 * (1 - {score['total']}/10)}}"
      stroke-linecap="round"/>
  </svg>
  <div class="score-text">{score['total']}</div>
  <div class="score-label">/ 10</div>
</div>

<!-- 告警概览 -->
<div class="grid">
  <div class="card">
    <h2>告警概览</h2>
    <div style="text-align:center; padding: 1rem 0;">
      <span class="status-badge badge-bad">🔴 Critical: {critical}</span>
      <span class="status-badge badge-warn">🟡 Warning: {warning}</span>
      <span class="status-badge badge-info">🟢 Info: {info}</span>
    </div>
    <p style="text-align:center; color: var(--text-dim); font-size: 0.85rem;">
      {'无告警，系统运行正常' if critical == 0 and warning == 0 else f'共 {critical + warning + info} 条告警，建议优先处理 Critical'}
    </p>
  </div>
  
  <div class="card">
    <h2>评分维度</h2>
    <div id="score-bars">
      <!-- JS fills this -->
    </div>
  </div>
</div>

<!-- 告警详情 -->
<div class="card" style="margin-bottom: 2rem;">
  <h2>告警详情</h2>
  {"".join([
    f'<div class="alert-item alert-{a["level"]}">'
    f'<strong>{"🔴" if a["level"]=="critical" else ("🟡" if a["level"]=="warning" else "🟢")} [{a["level"].upper()}]</strong> '
    f'<span style="color: var(--text-dim);">[{a["category"]}]</span> {a["item"]}<br>'
    f'<span style="color: var(--accent-dim); font-size: 0.85rem;">→ {a["suggestion"]}</span>'
    f'</div>'
    for a in alerts
  ]) if alerts else '<p style="color: var(--good); text-align: center; padding: 1rem;">✅ 无告警</p>'}
</div>

<!-- 项目状态 -->
<div class="card" style="margin-bottom: 2rem;">
  <h2>项目审计</h2>
  <table>
    <thead>
      <tr><th>项目</th><th>Tier</th><th>状态</th><th>文件</th><th>最后活跃</th><th>Blocker</th></tr>
    </thead>
    <tbody>
      {''.join([
        f'<tr>'
        f'<td><strong>{p["name"]}</strong></td>'
        f'<td>{p.get("tier", "-") or "-"}</td>'
        f'<td><span class="status-badge {"badge-good" if p["status"]=="active" else ("badge-warn" if p["status"]=="stale" else "badge-info")}">{p["status"]}</span></td>'
        f'<td>{p["file_count"]}</td>'
        f'<td>{p["age_hours"]:.0f}h</td>'
        f'<td style="color: var(--text-dim); font-size: 0.8rem;">{(p.get("blocker") or "-")[:25]}</td>'
        f'</tr>'
        for p in projects
      ])}
    </tbody>
  </table>
</div>

<div class="grid">
  <!-- 环境 -->
  <div class="card">
    <h2>运行环境</h2>
    <div class="metric"><span>主机</span><span class="metric-value">{env.get("hostname", "-")}</span></div>
    <div class="metric"><span>磁盘</span><span class="metric-value">{env.get("disk", {}).get("usage_percent", 0)}%</span></div>
    <div class="metric"><span>Node.js</span><span class="metric-value">{env.get("versions", {}).get("node", "-")}</span></div>
    <div class="metric"><span>Python</span><span class="metric-value">{env.get("versions", {}).get("python", "-")}</span></div>
    <div class="metric"><span>OpenClaw</span><span class="metric-value">{env.get("versions", {}).get("openclaw", "-")}</span></div>
  </div>
  
  <!-- Harness -->
  <div class="card">
    <h2>Harness 机制</h2>
    <div class="metric"><span>Cron Jobs</span><span class="metric-value">{harness.get("cron_jobs_count", 0)}</span></div>
    <div class="metric"><span>Gateway</span><span class="metric-value">{harness.get("gateway_status", "-")[:20]}</span></div>
    <div class="metric"><span>Sessions</span><span class="metric-value">{harness.get("sessions", {}).get("count", 0)} 个</span></div>
    <div class="metric"><span>Git 分支</span><span class="metric-value">{report.get("git", {}).get("branch", "-")}</span></div>
    <div class="metric"><span>未提交</span><span class="metric-value">{"有" if report.get("git", {}).get("has_uncommitted") else "无"}</span></div>
  </div>
  
  <!-- 记忆 -->
  <div class="card">
    <h2>记忆系统</h2>
    <div class="metric"><span>关键文件</span><span class="metric-value">{"✅" if memory.get("all_key_files_exist") else "❌"}</span></div>
    <div class="metric"><span>记忆文件</span><span class="metric-value">{memory.get("memory_files_count", 0)}</span></div>
    <div class="metric"><span>日记总数</span><span class="metric-value">{memory.get("diary_total_count", 0)}</span></div>
    <div class="metric"><span>7天日记</span><span class="metric-value">{memory.get("diary_recent_7d", 0)}</span></div>
  </div>
  
  <!-- 能力 -->
  <div class="card">
    <h2>能力验证</h2>
    <div class="metric"><span>GitHub CLI</span><span class="metric-value">{"✅" if cap.get("github_cli") else "❌"}</span></div>
    <div class="metric"><span>GitHub API</span><span class="metric-value">{"✅" if cap.get("github_api") else "❌"}</span></div>
    <div class="metric"><span>飞书</span><span class="metric-value">{"✅" if cap.get("feishu") else "❌"}</span></div>
    <div class="metric"><span>Tunnel</span><span class="metric-value">{"✅" if cap.get("cloudflare_tunnel") else "❌"}</span></div>
    <div class="metric"><span>邮件</span><span class="metric-value">{"✅" if cap.get("mailgun_webhook") else "❌"}</span></div>
  </div>
</div>

<!-- 详细数据 JSON -->
<div class="card" style="margin-bottom: 2rem;">
  <h2>原始数据（JSON）</h2>
  <details>
    <summary style="cursor: pointer; color: var(--accent);">点击展开完整 JSON 数据</summary>
    <pre style="margin-top: 1rem; padding: 1rem; background: #0a0a0f; border-radius: 8px; overflow-x: auto; font-size: 0.75rem; color: var(--text-dim);"><code id="raw-json"></code></pre>
  </details>
</div>

<!-- Skill 源码 -->
<div class="card" style="margin-bottom: 2rem;">
  <h2>📋 Skill 源码</h2>
  <p style="color: var(--text-dim); font-size: 0.85rem; margin-bottom: 1rem;">
    本报告由 P1.0 baseline-check Skill 自动生成。以下展示该 Skill 的完整文档和脚本源码，供审计和改进。
  </p>
  
  <details>
    <summary style="cursor: pointer; color: var(--accent); margin-bottom: 0.5rem;">
      📄 baseline-check-v2.md（Skill 文档）
    </summary>
    <pre style="margin-top: 0.5rem; padding: 1rem; background: #0a0a0f; border-radius: 8px; overflow-x: auto; font-size: 0.75rem; color: var(--text-dim); max-height: 400px; overflow-y: auto;"><code>{skill_doc_content}</code></pre>
  </details>
  
  <details style="margin-top: 1rem;">
    <summary style="cursor: pointer; color: var(--accent); margin-bottom: 0.5rem;">
      🐍 p1-baseline.py（检查脚本）
    </summary>
    <pre style="margin-top: 0.5rem; padding: 1rem; background: #0a0a0f; border-radius: 8px; overflow-x: auto; font-size: 0.75rem; color: var(--text-dim); max-height: 400px; overflow-y: auto;"><code>{skill_script_content}</code></pre>
  </details>
</div>

<footer>
  <p>小K · P1.0 自成长系统 · 全面状态检查</p>
  <p style="margin-top: 0.5rem;">报告由 p1-baseline.py 自动生成 · 部署于 littlek.trust4.net</p>
</footer>

</div>

<script>
// 评分维度柱状图
const scoreData = {score_data};
const scoreContainer = document.getElementById('score-bars');
for (const [dim, val] of Object.entries(scoreData)) {{
  const bar = document.createElement('div');
  bar.className = 'chart-bar';
  const label = {{'projects':'项目','environment':'环境','memory':'记忆','capabilities':'能力','trend':'趋势'}}[dim] || dim;
  bar.innerHTML = `
    <div class="chart-label">${{label}}</div>
    <div class="chart-fill" style="width: ${{val * 10}}%; background: ${{val >= 8 ? 'var(--good)' : (val >= 5 ? 'var(--accent)' : 'var(--warn)')}}" data-value="${{val}}"></div>
  `;
  scoreContainer.appendChild(bar);
}}

// 注入原始 JSON
const rawData = {json.dumps(report, indent=2, ensure_ascii=False)};
document.getElementById('raw-json').textContent = JSON.stringify(rawData, null, 2);
</script>

</body>
</html>
"""
    return html

def main():
    ensure_dirs()
    
    print("🔍 P1.0 全面状态检查启动...")
    
    # 收集所有数据
    data = {}
    
    print("  → 检查模型与运行时...")
    data["model"] = get_model_info()
    
    print("  → 检查系统环境...")
    data["environment"] = get_system_info()
    
    print("  → 检查 Harness 机制...")
    data["harness"] = get_harness_mechanisms()
    
    print("  → 检查记忆系统...")
    data["memory_system"] = get_memory_system()
    
    print("  → 审计项目...")
    data["projects"] = get_projects()
    
    print("  → 验证能力...")
    data["capabilities"] = get_capabilities()
    
    print("  → 检查会话历史...")
    data["session_history"] = get_session_history_summary()
    
    print("  → 检查 Git 状态...")
    data["git"] = get_git_info()
    
    # 生成报告
    print("📊 生成报告...")
    report = generate_json_report(data)
    
    # 写入 JSON
    json_path = f"{REPORTS_DIR}/latest.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  → JSON: {json_path}")
    
    # 写入 Markdown
    md_path = f"{REPORTS_DIR}/latest.md"
    md_content = generate_markdown_report(report)
    with open(md_path, "w") as f:
        f.write(md_content)
    print(f"  → Markdown: {md_path}")
    
    # 写入 HTML（部署到主页）
    html_path = f"{WORKSPACE}/p1-dashboard.html"
    html_content = generate_html_dashboard(report)
    with open(html_path, "w") as f:
        f.write(html_content)
    print(f"  → HTML: {html_path}")
    
    # 同时写入报告目录
    html_backup = f"{REPORTS_DIR}/latest.html"
    with open(html_backup, "w") as f:
        f.write(html_content)
    
    # 历史归档
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    hist_json = f"{REPORTS_DIR}/history/{timestamp}.json"
    hist_md = f"{REPORTS_DIR}/history/{timestamp}.md"
    with open(hist_json, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(hist_md, "w") as f:
        f.write(md_content)
    
    # 写入 state.json
    state_path = f"{SKILL_DIR}/state.json"
    state = {}
    if os.path.exists(state_path):
        try:
            with open(state_path, "r") as f:
                state = json.load(f)
        except:
            pass
    state["last_baseline"] = report
    state["last_run"] = datetime.now().isoformat()
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    
    # 输出摘要
    print(f"""
{'='*60}
✅ P1.0 检查完成
{'='*60}
评分：{report['score']['total']}/10（{report['score']['grade']} 级）
项目：{len(report['projects'])} 个（active {len([p for p in report['projects'] if p['status']=='active'])}, stale {len([p for p in report['projects'] if p['status']=='stale'])}）
告警：🔴 {report['alert_count']['critical']} 🟡 {report['alert_count']['warning']} 🟢 {report['alert_count']['info']}
{'='*60}
""")
    
    return report

if __name__ == "__main__":
    main()
