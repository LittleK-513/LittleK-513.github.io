#!/usr/bin/env python3
"""check-infrastructure.py — 基础设施检查模块（Tunnel / 邮件 / SSH / 身份 / 通道）
独立运行输出 JSON：python3 check-infrastructure.py
"""

import os, json, subprocess, time
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"


def run_cmd(cmd, timeout=15):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(),
                "returncode": result.returncode, "ok": result.returncode == 0}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "ok": False}


def check():
    checks_passed = 0
    checks_total = 6

    infra = {}

    # ── I0.1 Cloudflare Tunnel ──
    tunnel = {}
    # 检查进程
    tunnel_proc = run_cmd("pgrep -a cloudflared 2>/dev/null || echo 'not running'")
    tunnel["process"] = tunnel_proc["stdout"]
    tunnel["running"] = "not running" not in tunnel_proc["stdout"]

    # 检查端口 20241（Cloudflare Tunnel 默认本地端口）
    port_check = run_cmd("ss -tlnp | grep ':20241' || echo 'no listener'")
    tunnel["port_20241"] = "no listener" not in port_check["stdout"]

    # 域名可达性
    domain_check = run_cmd("curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://littlek.trust4.net 2>/dev/null || echo '000'")
    tunnel["domain_reachable"] = domain_check["stdout"] in ["200", "301", "302", "404"]
    tunnel["domain_http_code"] = domain_check["stdout"]

    # 隧道状态（cloudflared 状态）
    tunnel_info = run_cmd("cloudflared tunnel list 2>/dev/null | head -5 || echo 'cloudflared not available'")
    tunnel["tunnel_list"] = tunnel_info["stdout"]

    if tunnel["running"] and tunnel["domain_reachable"]:
        checks_passed += 1

    infra["cloudflare_tunnel"] = tunnel

    # ── I0.2 邮件系统 ──
    mail = {}
    mail_systemd = run_cmd("systemctl is-active xiaok-mailbox-webhook 2>/dev/null || echo 'inactive'")
    mail["systemd_active"] = "active" in mail_systemd["stdout"]
    mail["systemd_status"] = mail_systemd["stdout"]

    # 邮件服务进程
    mail_proc = run_cmd("pgrep -f 'email-webhook-server' 2>/dev/null || echo 'not running'")
    mail["process_running"] = "not running" not in mail_proc["stdout"]

    # 最近投递日志（通过日志文件存在性和修改时间推断）
    log_paths = [
        "/var/log/xiaok-mailbox.log",
        "/var/log/openclaw-email.log",
    ]
    latest_delivery = None
    for log_path in log_paths:
        if os.path.exists(log_path):
            try:
                stat = os.stat(log_path)
                age_hours = (time.time() - stat.st_mtime) / 3600
                latest_delivery = {
                    "log_file": log_path,
                    "last_modified_hours": round(age_hours, 1),
                }
                break
            except:
                pass
    mail["latest_delivery"] = latest_delivery

    if mail["systemd_active"]:
        checks_passed += 1

    infra["mail_system"] = mail

    # ── I0.3 GitHub 身份 ──
    github = {}
    gh_auth = run_cmd("gh auth status 2>1 | head -5")
    github["cli_logged_in"] = "Logged in" in gh_auth["stdout"] or gh_auth["ok"]
    github["auth_status_raw"] = gh_auth["stdout"]

    # PAT 有效期（无法直接查询，通过 gh api 调用测试推断）
    gh_api = run_cmd("gh api user 2>1 | head -1")
    github["api_ok"] = gh_api["ok"] and "login" in gh_api["stdout"]
    github["api_raw"] = gh_api["stdout"]

    # Git 配置
    git_user = run_cmd("git config user.name 2>/dev/null || echo 'not set'")
    git_email = run_cmd("git config user.email 2>/dev/null || echo 'not set'")
    github["git_user"] = git_user["stdout"]
    github["git_email"] = git_email["stdout"]

    if github["cli_logged_in"]:
        checks_passed += 1

    infra["github_identity"] = github

    # ── I0.4 飞书连接 ──
    feishu = {}
    token_paths = [
        "/root/.openclaw/.feishu_token",
        f"{WORKSPACE}/.feishu_token",
    ]
    token_exists = any(os.path.exists(p) for p in token_paths)
    feishu["token_present"] = token_exists

    # 检查飞书通道配置
    feishu_channel = "/root/.openclaw/channels/feishu"
    feishu["channel_configured"] = os.path.exists(feishu_channel)

    if token_exists:
        checks_passed += 1

    infra["feishu_connection"] = feishu

    # ── I0.5 微信通道 ──
    weixin = {}
    weixin_channel = "/root/.openclaw/channels/weixin"
    weixin["channel_configured"] = os.path.exists(weixin_channel)

    # 微信进程
    weixin_proc = run_cmd("pgrep -f 'weixin' 2>/dev/null || echo 'not running'")
    weixin["process_running"] = "not running" not in weixin_proc["stdout"]

    # 健康检查日志
    weixin_health_log = "/var/log/openclaw_weixin_health.log"
    if os.path.exists(weixin_health_log):
        try:
            stat = os.stat(weixin_health_log)
            weixin["health_log_age_hours"] = round((time.time() - stat.st_mtime) / 3600, 1)
        except:
            weixin["health_log_age_hours"] = None

    if weixin["channel_configured"]:
        checks_passed += 1

    infra["weixin_channel"] = weixin

    # ── I0.6 美国主机出口 (Dreamhost SSH) ──
    dreamhost = {}
    ssh_key = f"{os.path.expanduser('~')}/.ssh/id_rsa"
    dreamhost["ssh_key_present"] = os.path.exists(ssh_key)

    # SSH 配置
    ssh_config = f"{os.path.expanduser('~')}/.ssh/config"
    dreamhost["ssh_config_present"] = os.path.exists(ssh_config)

    if os.path.exists(ssh_config):
        try:
            with open(ssh_config, "r") as f:
                config_text = f.read()
            dreamhost["has_dreamhost_entry"] = "dreamhost" in config_text.lower()
        except:
            dreamhost["has_dreamhost_entry"] = False

    # 尝试 SSH 连接（dry-run）
    ssh_test = run_cmd("ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new dreamhost 'echo ok' 2>1 || echo 'failed'")
    dreamhost["ssh_test_ok"] = "ok" in ssh_test["stdout"]
    dreamhost["ssh_test_raw"] = ssh_test["stdout"][:100]

    if dreamhost["ssh_key_present"]:
        checks_passed += 1

    infra["dreamhost_ssh"] = dreamhost

    data = {
        "groups": [
            {"id": "I0.1", "name": "Cloudflare Tunnel", "status": "✅" if tunnel["running"] else "❌", "details": tunnel},
            {"id": "I0.2", "name": "邮件系统 (xiaok-mailbox-webhook)", "status": "✅" if mail["systemd_active"] else "❌", "details": mail},
            {"id": "I0.3", "name": "GitHub 身份 (LittleK-513)", "status": "✅" if github["cli_logged_in"] else "❌", "details": github},
            {"id": "I0.4", "name": "飞书连接", "status": "✅" if feishu["token_present"] else "❌", "details": feishu},
            {"id": "I0.5", "name": "微信通道", "status": "✅" if weixin["channel_configured"] else "❌", "details": weixin},
            {"id": "I0.6", "name": "Dreamhost SSH", "status": "✅" if dreamhost["ssh_key_present"] else "❌", "details": dreamhost},
        ],
        "infra": infra,
    }

    return {"module": "infrastructure", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
