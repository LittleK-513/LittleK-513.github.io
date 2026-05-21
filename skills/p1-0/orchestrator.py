#!/usr/bin/env python3
"""orchestrator.py — P1.0 baseline-check 编排器
并行运行所有检查模块，收集输出，计算评分，生成告警
用法：python3 orchestrator.py
输出：统一 JSON 到 stdout，同时写入 reports/p1-0/latest.json
"""

import os, sys, json, subprocess, time, glob
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKSPACE = "/root/.openclaw/workspace"
MODULES_DIR = f"{WORKSPACE}/skills/p1-0/modules"
REPORTS_DIR = f"{WORKSPACE}/reports/p1-0"

def run_module(script_path, timeout=30):
    """运行单个模块，返回 JSON 输出或错误信息"""
    try:
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True, text=True, timeout=timeout,
            cwd=MODULES_DIR
        )
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"module": os.path.basename(script_path), "error": "invalid JSON", "raw": result.stdout[:500]}
        else:
            return {"module": os.path.basename(script_path), "error": result.stderr[:500], "raw": result.stdout[:500]}
    except subprocess.TimeoutExpired:
        return {"module": os.path.basename(script_path), "error": "timeout", "checks_passed": 0, "checks_total": 0}
    except Exception as e:
        return {"module": os.path.basename(script_path), "error": str(e), "checks_passed": 0, "checks_total": 0}

def calculate_score(modules_data):
    """计算系统健康分
    项目30% + 环境20% + 记忆20% + 能力20% + 趋势10%
    """
    score = 0
    breakdown = {}
    
    # 项目健康 (30%)
    projects_mod = modules_data.get("projects", {})
    projects_data = projects_mod.get("data", {})
    projects_list = projects_data.get("projects", [])
    active = len([p for p in projects_list if p.get("status") == "active"])
    total = len(projects_list)
    if total > 0:
        project_score = min(10, (active / total) * 10)
    else:
        project_score = 5
    breakdown["projects"] = round(project_score, 1)
    score += project_score * 0.30
    
    # 环境稳定 (20%)
    env_mod = modules_data.get("environment", {})
    env_data = env_mod.get("data", {})
    disk_pct = env_data.get("disk", {}).get("usage_percent", 0)
    env_checks = env_mod.get("checks_passed", 0)
    env_total = env_mod.get("checks_total", 1)
    env_score = min(10, (env_checks / max(env_total, 1)) * 10)
    if disk_pct > 85:
        env_score -= 2
    if disk_pct > 95:
        env_score -= 3
    breakdown["environment"] = round(max(0, env_score), 1)
    score += max(0, env_score) * 0.20
    
    # 记忆完整 (20%)
    mem_mod = modules_data.get("memory", {})
    mem_data = mem_mod.get("data", {})
    mem_score = 10 if mem_data.get("all_key_files_exist") else 5
    if mem_data.get("diary_recent_7d", 0) < 3:
        mem_score -= 2
    breakdown["memory"] = round(max(0, mem_score), 1)
    score += max(0, mem_score) * 0.20
    
    # 能力可用 (20%)
    cap_mod = modules_data.get("capabilities", {})
    cap_data = cap_mod.get("data", {})
    cap_list = [cap_data.get("github_cli"), cap_data.get("github_api"),
                cap_data.get("feishu"), cap_data.get("cloudflare_tunnel")]
    available = sum(1 for c in cap_list if c)
    cap_score = (available / len(cap_list)) * 10 if cap_list else 5
    breakdown["capabilities"] = round(cap_score, 1)
    score += cap_score * 0.20
    
    # 历史趋势 (10%)
    trend_score = 5  # 默认持平，后续版本可从 state.json 对比
    breakdown["trend"] = trend_score
    score += trend_score * 0.10
    
    return round(score, 1), breakdown

def generate_alerts(modules_data):
    """从模块数据生成告警清单"""
    alerts = []
    
    # 项目告警
    projects_mod = modules_data.get("projects", {})
    for p in projects_mod.get("data", {}).get("projects", []):
        if p.get("status") == "stale":
            alerts.append({
                "level": "warning",
                "category": "project",
                "item": f"{p['name']} stale {p['age_hours']:.0f}h",
                "suggestion": f"检查 {p['name']} 的 blocker 或推进 next action",
            })
        elif p.get("status") == "ghost":
            alerts.append({
                "level": "info",
                "category": "project",
                "item": f"{p['name']} 是 ghost 项目",
                "suggestion": "归档或填充内容",
            })
    
    # 环境告警
    env_mod = modules_data.get("environment", {})
    env_data = env_mod.get("data", {})
    disk_pct = env_data.get("disk", {}).get("usage_percent", 0)
    if disk_pct > 85:
        alerts.append({
            "level": "critical",
            "category": "environment",
            "item": f"磁盘使用率 {disk_pct}%",
            "suggestion": "清理日志和旧 session 文件",
        })
    
    # 记忆告警
    mem_mod = modules_data.get("memory", {})
    mem_data = mem_mod.get("data", {})
    if not mem_data.get("all_key_files_exist"):
        missing = [k for k, v in mem_data.get("key_files", {}).items() if not v or not v.get("exists")]
        alerts.append({
            "level": "critical",
            "category": "memory",
            "item": f"关键文件缺失: {', '.join(missing)}",
            "suggestion": "从 git 恢复或重建文件",
        })
    if mem_data.get("diary_recent_7d", 0) == 0:
        alerts.append({
            "level": "warning",
            "category": "memory",
            "item": "7 天内无日记记录",
            "suggestion": "检查内观机制是否正常运行",
        })
    
    # 能力告警
    cap_mod = modules_data.get("capabilities", {})
    cap_data = cap_mod.get("data", {})
    if not cap_data.get("github_api"):
        alerts.append({
            "level": "warning",
            "category": "capability",
            "item": "GitHub API 不可用",
            "suggestion": "检查 PAT 是否过期",
        })
    
    # 模块失败告警
    for name, mod in modules_data.items():
        if "error" in mod and mod["error"]:
            alerts.append({
                "level": "critical",
                "category": "module",
                "item": f"模块 {name} 运行失败: {mod['error']}",
                "suggestion": "检查模块脚本",
            })
    
    # 排序
    level_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: level_order.get(x["level"], 99))
    
    return alerts

def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(f"{REPORTS_DIR}/history", exist_ok=True)
    
    print("🔍 P1.0 baseline-check orchestrator 启动...")
    
    # 发现所有模块
    module_scripts = sorted(glob.glob(f"{MODULES_DIR}/check-*.py"))
    print(f"  → 发现 {len(module_scripts)} 个检查模块")
    
    # 并行运行所有模块
    modules_data = {}
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(run_module, path): os.path.basename(path).replace(".py", "") for path in module_scripts}
        for future in as_completed(futures):
            module_name = futures[future]
            try:
                result = future.result()
                key = result.get("module", module_name)
                modules_data[key] = result
                error = result.get("error")
                if error:
                    print(f"  ⚠️ {key}: {error}")
                else:
                    passed = result.get("checks_passed", 0)
                    total = result.get("checks_total", 0)
                    print(f"  ✅ {key}: {passed}/{total} 通过")
            except Exception as e:
                print(f"  ❌ {module_name}: {e}")
                modules_data[module_name] = {"module": module_name, "error": str(e), "checks_passed": 0, "checks_total": 0}
    
    # 计算评分
    print("📊 计算评分...")
    score, breakdown = calculate_score(modules_data)
    alerts = generate_alerts(modules_data)
    
    # 组装统一报告
    report = {
        "meta": {
            "version": "p1-baseline-v2-modular",
            "generated_at": datetime.now().isoformat(),
            "workspace": WORKSPACE,
            "modules_run": len(module_scripts),
            "modules_ok": sum(1 for m in modules_data.values() if "error" not in m or not m.get("error")),
        },
        "score": {
            "total": score,
            "max": 10,
            "breakdown": breakdown,
            "grade": "A" if score >= 8 else ("B" if score >= 6 else ("C" if score >= 4 else "D")),
        },
        "modules": modules_data,
        "alerts": alerts,
        "alert_count": {
            "critical": len([a for a in alerts if a["level"] == "critical"]),
            "warning": len([a for a in alerts if a["level"] == "warning"]),
            "info": len([a for a in alerts if a["level"] == "info"]),
        },
    }
    
    # 写入 latest.json
    json_path = f"{REPORTS_DIR}/latest.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  → JSON: {json_path}")
    
    # 写入 state.json
    state_path = f"{WORKSPACE}/skills/p1-0/state.json"
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
评分：{score}/10（{report['score']['grade']} 级）
模块：{report['meta']['modules_ok']}/{report['meta']['modules_run']} 成功
告警：🔴 {report['alert_count']['critical']} 🟡 {report['alert_count']['warning']} 🟢 {report['alert_count']['info']}
{'='*60}
""")
    
    # 同时输出到 stdout
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report

if __name__ == "__main__":
    main()
