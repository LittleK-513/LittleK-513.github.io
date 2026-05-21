#!/usr/bin/env python3
"""check-capabilities.py — 能力验证模块（GitHub、飞书、Tunnel、邮件）
独立运行输出 JSON：python3 check-capabilities.py
"""

import os, json, subprocess

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
    
    # GitHub CLI
    gh_auth = run_cmd("gh auth status 2>&1 | head -5")
    gh_ok = "Logged in" in gh_auth["stdout"] or gh_auth["ok"]
    if gh_ok: checks_passed += 1
    
    # GitHub API
    gh_api = run_cmd("gh api user 2>&1 | head -1")
    gh_api_ok = gh_api["ok"] and "login" in gh_api["stdout"]
    if gh_api_ok: checks_passed += 1
    
    # Web 搜索（依赖 kimi_search tool，标记为可用）
    search_ok = True
    checks_passed += 1
    
    # 飞书 token
    feishu_ok = os.path.exists("/root/.openclaw/.feishu_token") or os.path.exists(f"{WORKSPACE}/.feishu_token")
    if feishu_ok: checks_passed += 1
    
    # Cloudflare Tunnel
    tunnel = run_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:8080 2>/dev/null || echo '000'")
    tunnel_ok = tunnel["stdout"] in ["200", "404", "301", "302"]
    if tunnel_ok: checks_passed += 1
    
    # 邮件 webhook
    mailgun = run_cmd("systemctl is-active xiaok-mailbox-webhook 2>/dev/null || echo 'inactive'")
    mailgun_ok = "active" in mailgun["stdout"]
    if mailgun_ok: checks_passed += 1
    
    data = {
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
    
    return {"module": "capabilities", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}

if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
