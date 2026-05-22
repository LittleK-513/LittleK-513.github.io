#!/usr/bin/env python3
"""check-harness-v2.py — Harness 机制检查模块 v2（Cron 归属 + Linux 资源 + OpenClaw 架构）
独立运行输出 JSON：python3 check-harness-v2.py
"""

import os, json, subprocess, glob, time, re
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"
SCRIPTS_DIR = "/root/.openclaw/scripts"


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


def parse_cron_jobs():
    """解析 crontab，返回带归属的 cron job 列表"""
    cron = run_cmd("crontab -l 2>/dev/null || echo 'no crontab'")
    lines = cron["stdout"].split("\n")

    # Cron 归属映射表：pattern → (项目归属, 描述)
    OWNERSHIP_MAP = {
        "resource-tracker": ("P1.3", "资源感知舱数据采集"),
        "sync-dashboard-data": ("P1.6", "网站数据同步"),
        "tracker-health-check": ("P1.3", "资源感知舱健康检查"),
        "cfm_backup": ("P3.2", "CFMS 数据备份"),
        "cfm_scraper": ("P3.2", "CFMS 数据抓取"),
        "daily_health": ("系统健康", "系统健康监控"),
        "weixin_health": ("I0.5", "微信通道健康检查"),
        "session-cleanup": ("P1.5", "Session 清理归档"),
        "momentum-trigger": ("P1.4", "心跳/内观机制"),
        "stargate": ("I0.1", "腾讯云监控"),
    }

    jobs = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 解析 cron 表达式（取前5个字段后的命令部分）
        parts = line.split()
        if len(parts) < 6:
            continue

        schedule = " ".join(parts[:5])
        command = " ".join(parts[5:])

        # 识别归属
        owner = "未分类"
        owner_tier = "?"
        description = ""
        for pattern, (tier, desc) in OWNERSHIP_MAP.items():
            if pattern in command:
                owner = tier
                owner_tier = tier.split(".")[0] if "." in tier else tier
                description = desc
                break

        jobs.append({
            "schedule": schedule,
            "command": command[:120],
            "owner": owner,
            "owner_tier": owner_tier,
            "description": description,
            "raw": line,
        })

    return jobs


def check_linux_resources():
    """详细 Linux 系统资源监控"""
    resources = {}

    # CPU 负载
    loadavg = run_cmd("cat /proc/loadavg")
    if loadavg["ok"]:
        parts = loadavg["stdout"].split()
        if len(parts) >= 3:
            resources["cpu_load"] = {
                "1min": float(parts[0]),
                "5min": float(parts[1]),
                "15min": float(parts[2]),
                "raw": loadavg["stdout"],
            }

    # 内存详细
    mem = run_cmd("free -m")
    if mem["ok"]:
        lines = mem["stdout"].split("\n")
        mem_info = {}
        for line in lines:
            if line.startswith("Mem:"):
                parts = line.split()
                if len(parts) >= 7:
                    mem_info = {
                        "total_mb": int(parts[1]),
                        "used_mb": int(parts[2]),
                        "free_mb": int(parts[3]),
                        "shared_mb": int(parts[4]),
                        "buffers_mb": int(parts[5]),
                        "cache_mb": int(parts[6]),
                        "available_mb": int(parts[6]) if len(parts) >= 7 else None,
                    }
            elif line.startswith("Swap:"):
                parts = line.split()
                if len(parts) >= 3:
                    mem_info["swap_total_mb"] = int(parts[1])
                    mem_info["swap_used_mb"] = int(parts[2])
        resources["memory"] = mem_info
        resources["memory_raw"] = mem["stdout"]

    # 磁盘各分区
    df = run_cmd("df -h")
    if df["ok"]:
        disk_partitions = []
        for line in df["stdout"].split("\n")[1:]:
            parts = line.split()
            if len(parts) >= 6:
                try:
                    usage_pct = int(parts[4].rstrip("%"))
                except:
                    usage_pct = 0
                disk_partitions.append({
                    "filesystem": parts[0],
                    "size": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "usage_percent": usage_pct,
                    "mount": parts[5],
                })
        resources["disk_partitions"] = disk_partitions

    # 进程数 / 僵尸进程
    ps = run_cmd("ps aux | wc -l")
    zombie = run_cmd("ps aux | grep 'Z' | grep -v grep | wc -l")
    resources["processes"] = {
        "total": int(ps["stdout"]) if ps["ok"] else 0,
        "zombie": int(zombie["stdout"]) if zombie["ok"] else 0,
    }

    # 系统运行时间
    uptime = run_cmd("uptime -p 2>/dev/null || uptime")
    resources["uptime_pretty"] = uptime["stdout"] if uptime["ok"] else "unknown"

    # CPU 信息
    cpuinfo = run_cmd("nproc")
    resources["cpu_cores"] = int(cpuinfo["stdout"]) if cpuinfo["ok"] else 0

    return resources


def check_openclaw_architecture():
    """OpenClaw/KimiClaw 架构状态"""
    arch = {}

    # Gateway 配置与状态
    gateway_config = run_cmd("openclaw gateway status 2>/dev/null || echo 'unknown'")
    gateway_ok = "running" in gateway_config["stdout"].lower() or "active" in gateway_config["stdout"].lower()

    # 尝试读取 gateway 配置
    gateway_port = "?"
    gateway_bind = "?"
    gateway_version = "?"
    config_path = "/root/.openclaw/config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config_text = f.read()
            port_match = re.search(r'port:\s*(\d+)', config_text)
            if port_match:
                gateway_port = port_match.group(1)
            bind_match = re.search(r'bind:\s*([\d.:]+)', config_text)
            if bind_match:
                gateway_bind = bind_match.group(1)
            ver_match = re.search(r'version:\s*([\w.-]+)', config_text)
            if ver_match:
                gateway_version = ver_match.group(1)
        except:
            pass

    arch["gateway"] = {
        "status": gateway_config["stdout"],
        "ok": gateway_ok,
        "port": gateway_port,
        "bind": gateway_bind,
        "version": gateway_version,
    }

    # Gateway heartbeat（通过最近日志推断）
    log_paths = [
        "/root/.openclaw/logs/gateway.log",
        "/var/log/openclaw/gateway.log",
    ]
    last_heartbeat = None
    for log_path in log_paths:
        if os.path.exists(log_path):
            try:
                stat = os.stat(log_path)
                last_heartbeat = round((time.time() - stat.st_mtime) / 60, 1)
                break
            except:
                pass
    arch["gateway"]["last_log_age_min"] = last_heartbeat

    # Channels 状态
    channels = {}

    # 微信通道
    weixin_ok = os.path.exists("/root/.openclaw/channels/weixin")
    weixin_pid = run_cmd("pgrep -f 'weixin' || echo ''")
    channels["weixin"] = {
        "configured": weixin_ok,
        "process_running": bool(weixin_pid["stdout"].strip()),
        "pid": weixin_pid["stdout"].strip() or None,
    }

    # 飞书通道
    feishu_ok = os.path.exists("/root/.openclaw/channels/feishu")
    channels["feishu"] = {
        "configured": feishu_ok,
        "token_present": os.path.exists("/root/.openclaw/.feishu_token") or os.path.exists(f"{WORKSPACE}/.feishu_token"),
    }

    # Web 通道
    channels["web"] = {
        "configured": True,  # 默认总是可用
    }

    # 邮件通道
    mail_systemd = run_cmd("systemctl is-active xiaok-mailbox-webhook 2>/dev/null || echo 'inactive'")
    channels["mail"] = {
        "systemd_active": "active" in mail_systemd["stdout"],
        "systemd_status": mail_systemd["stdout"],
    }

    arch["channels"] = channels

    # Sessions 状态
    sessions_dir = "/root/.openclaw/agents/main/sessions"
    sessions = glob.glob(f"{sessions_dir}/*.jsonl") if os.path.exists(sessions_dir) else []
    total_size = sum(os.path.getsize(s) for s in sessions)

    # 活跃 session（最近1小时有消息）
    active_sessions = []
    for s in sessions:
        try:
            mtime = os.path.getmtime(s)
            age_hours = (time.time() - mtime) / 3600
            if age_hours < 1:
                size = os.path.getsize(s)
                active_sessions.append({
                    "file": os.path.basename(s),
                    "size": human_size(size),
                    "age_hours": round(age_hours, 2),
                })
        except:
            pass

    arch["sessions"] = {
        "total_count": len(sessions),
        "total_size": human_size(total_size),
        "total_size_bytes": total_size,
        "active_recent_1h": len(active_sessions),
        "active_sessions": active_sessions[:5],
    }

    # Context 压力（估算）
    # 通过会话文件大小估算上下文压力
    context_pressure = "low"
    if total_size > 100 * 1024 * 1024:  # 100MB
        context_pressure = "high"
    elif total_size > 50 * 1024 * 1024:
        context_pressure = "medium"
    arch["context_pressure"] = {
        "level": context_pressure,
        "total_sessions_size_mb": round(total_size / (1024 * 1024), 2),
    }

    # Tools 清单
    tools = {
        "official": [],
        "custom": [],
    }

    # 检查常用自定义 tools
    custom_tools = [
        ("cloudflared_tunnel", "/usr/bin/cloudflared", "Cloudflare Tunnel"),
        ("ssh_dreamhost", f"{os.path.expanduser('~')}/.ssh/id_rsa", "SSH Dreamhost"),
        ("email_webhook", "/root/.openclaw/scripts/email-webhook-server.js", "邮件 Webhook"),
        ("resource_tracker", "/root/.openclaw/scripts/resource-tracker.py", "资源感知舱"),
        ("momentum_trigger", "/root/.openclaw/scripts/momentum-trigger.sh", "动量触发器"),
    ]
    for tool_id, path, desc in custom_tools:
        exists = os.path.exists(path)
        tools["custom"].append({
            "id": tool_id,
            "path": path,
            "description": desc,
            "available": exists,
        })

    arch["tools"] = tools

    # Plugins
    plugins_dir = "/root/.openclaw/plugins"
    plugins = []
    if os.path.exists(plugins_dir):
        for item in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item)
            if os.path.isdir(item_path):
                plugins.append({
                    "name": item,
                    "path": item_path,
                })
    arch["plugins"] = plugins

    return arch


def check():
    checks_passed = 0
    checks_total = 6

    # 配置文件
    config_paths = ["/root/.openclaw/config.yaml", "/root/.openclaw/config.yml", "/root/.openclaw/.env"]
    config_status = {}
    configs_ok = 0
    for path in config_paths:
        info = get_file_info(path)
        config_status[path] = info or {"exists": False}
        if info and info["exists"]:
            configs_ok += 1
    if configs_ok > 0:
        checks_passed += 1

    # Cron Jobs（带归属）
    cron_jobs = parse_cron_jobs()
    checks_passed += 1  # cron 可查询即算通过

    # Gateway 状态
    gateway = run_cmd("openclaw gateway status 2>/dev/null || echo 'unknown'")
    gateway_ok = "running" in gateway["stdout"].lower() or "active" in gateway["stdout"].lower()
    if gateway_ok:
        checks_passed += 1

    # systemd 服务
    systemd = run_cmd("systemctl list-units --type=service --state=running | grep -i openclaw || echo 'none'")
    systemd_ok = systemd["stdout"] and systemd["stdout"] != "none"
    if systemd_ok:
        checks_passed += 1

    # session 文件
    sessions_dir = "/root/.openclaw/agents/main/sessions"
    sessions = glob.glob(f"{sessions_dir}/*.jsonl") if os.path.exists(sessions_dir) else []
    total_size = sum(os.path.getsize(s) for s in sessions)
    session_ok = len(sessions) > 0
    if session_ok:
        checks_passed += 1

    # Linux 资源
    linux_resources = check_linux_resources()
    resources_ok = linux_resources.get("cpu_load") is not None
    if resources_ok:
        checks_passed += 1

    # OpenClaw 架构
    openclaw_arch = check_openclaw_architecture()

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
        "linux_resources": linux_resources,
        "openclaw_architecture": openclaw_arch,
    }

    return {"module": "harness", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
