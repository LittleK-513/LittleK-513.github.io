#!/usr/bin/env python3
"""orchestrator.py — P1.0 baseline-check 编排器 v3
并行运行所有检查模块，收集输出，AI 分析，期望 vs 现实对比，计算评分，生成告警
用法：python3 orchestrator.py
输出：统一 JSON 到 stdout，同时写入 reports/p1-0/latest.json
"""

import os, sys, json, subprocess, time, glob, re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKSPACE = "/root/.openclaw/workspace"
MODULES_DIR = f"{WORKSPACE}/skills/p1-0/modules"
REPORTS_DIR = f"{WORKSPACE}/reports/p1-0"
STATE_DIR = f"{WORKSPACE}/references/self-evolution/state"
MEMORY_PATH = f"{WORKSPACE}/MEMORY.md"


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


def load_expected_state():
    """读取 MEMORY.md 和 P*.json 作为期望状态"""
    expected = {}

    # 读取 P*.json 状态文件
    for tier in ["P0", "P1", "P2", "P3"]:
        path = f"{STATE_DIR}/{tier}.json"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                expected[tier] = {
                    "source": f"{tier}.json",
                    "current_step": data.get("current_step") or data.get("current_phase"),
                    "last_action": data.get("last_action", "")[:200],
                    "blocker": data.get("blocker") or data.get("waiting_for"),
                    "last_updated": data.get("last_updated"),
                    "next_steps": [s.get("task", s.get("id", "")) for s in data.get("next_steps", [])[:2]],
                }
            except Exception as e:
                expected[tier] = {"source": f"{tier}.json", "error": str(e)}

    # 从 MEMORY.md 提取关键期望线索
    memory_expectations = {}
    if os.path.exists(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                mem_text = f.read()
            # 提取 P0 相关期望
            if "bounty" in mem_text.lower() or "github" in mem_text.lower():
                memory_expectations["P0"] = "记忆中关注 bounty / GitHub 赚钱任务"
            if "自进化" in mem_text or "P1" in mem_text or "Cycle" in mem_text:
                memory_expectations["P1"] = "记忆中 P1 自进化 / Cycle 循环在推进"
            if "社交" in mem_text or "Moltbook" in mem_text or "Colony" in mem_text:
                memory_expectations["P2"] = "记忆中社交网络 / Moltbook / Colony 互动"
        except:
            pass

    return {"files": expected, "memory_hints": memory_expectations}


def perform_ai_analysis(modules_data):
    """
    AI 分析所有模块数据，产出定性洞察。
    规则驱动 + 启发式，模拟大模型分析思维。
    返回结构化分析结果。
    """
    analysis = {
        "summary": "",
        "tier_insights": {},
        "anomalies": [],
        "trends": [],
        "recommendations": [],
        "health_assessment": {},
    }

    # 提取关键数据
    projects_mod = modules_data.get("projects", {})
    groups = projects_mod.get("data", {}).get("groups", [])
    flat_projects = projects_mod.get("data", {}).get("flat_projects", [])
    special_artifacts = projects_mod.get("data", {}).get("special_artifacts", [])
    env_mod = modules_data.get("environment", {})
    env_data = env_mod.get("data", {})
    mem_mod = modules_data.get("memory", {})
    mem_data = mem_mod.get("data", {})
    cap_mod = modules_data.get("capabilities", {})
    cap_data = cap_mod.get("data", {})
    harness_mod = modules_data.get("harness", {})
    harness_data = harness_mod.get("data", {})
    infra_mod = modules_data.get("infrastructure", {})
    infra_data = infra_mod.get("data", {})
    infra_groups = infra_data.get("groups", []) if infra_data else []

    # ── 1. 项目群健康度评估 ──
    for g in groups:
        tier = g["tier"]
        stats = g["stats"]
        projects = g["projects"]

        health_notes = []
        if stats["active"] == stats["total"]:
            health_notes.append(f"✅ {tier} 所有 {stats['total']} 个项目均活跃")
        elif stats["stale"] > 0:
            health_notes.append(f"⚠️ {tier} 有 {stats['stale']}/{stats['total']} 个项目停滞")
            # 找出最老 stale
            stale_projs = [p for p in projects if p["status"] == "stale"]
            if stale_projs:
                oldest = max(stale_projs, key=lambda x: x["age_hours"])
                health_notes.append(f"   最老停滞: {oldest['name']} ({oldest['age_hours']:.0f}h)")
        if stats["orphan"] > 0:
            health_notes.append(f"⚪ {tier} 有 {stats['orphan']} 个 orphan 项目需整理")

        analysis["health_assessment"][tier] = {
            "score": g.get("group_score", 0),
            "status": g.get("group_status", "unknown"),
            "notes": health_notes,
        }

    # ── 2. 异常识别 ──
    anomalies = []

    # 磁盘异常
    disk_pct = env_data.get("disk", {}).get("usage_percent", 0)
    if disk_pct > 85:
        anomalies.append({
            "severity": "high",
            "category": "environment",
            "finding": f"磁盘使用率 {disk_pct}% 超过 85% 阈值",
            "detail": "可能引发日志写入失败或 session 无法保存",
        })

    # 项目停滞异常
    for p in flat_projects:
        if p["status"] == "stale" and p["age_hours"] > 72:
            anomalies.append({
                "severity": "medium",
                "category": "project",
                "finding": f"{p['name']} 已停滞 {p['age_hours']:.0f}h（超过3天）",
                "detail": f"最后动作: {p.get('last_action') or '无记录'}",
            })
        if p["status"] == "ghost":
            anomalies.append({
                "severity": "low",
                "category": "project",
                "finding": f"{p['name']} 是 ghost 项目（空目录）",
                "detail": "建议归档或填充内容",
            })

    # 关键文件缺失
    if not mem_data.get("all_key_files_exist"):
        missing = [k for k, v in mem_data.get("key_files", {}).items() if not v or not v.get("exists")]
        anomalies.append({
            "severity": "high",
            "category": "memory",
            "finding": f"关键记忆文件缺失: {', '.join(missing)}",
            "detail": "核心身份和记忆可能丢失",
        })

    # 日记断更
    diary_7d = mem_data.get("diary_recent_7d", 0)
    if diary_7d == 0:
        anomalies.append({
            "severity": "medium",
            "category": "memory",
            "finding": "7 天内无日记记录",
            "detail": "内观机制可能未正常运行",
        })

    # 系统资源异常
    linux_res = harness_data.get("linux_resources", {})
    cpu_load = linux_res.get("cpu_load", {})
    if cpu_load:
        load_1min = cpu_load.get("1min", 0)
        cpu_cores = linux_res.get("cpu_cores", 1)
        if load_1min > cpu_cores * 2:
            anomalies.append({
                "severity": "high",
                "category": "system_resources",
                "finding": f"CPU 1分钟负载 {load_1min} 超过核心数 {cpu_cores} 的2倍",
                "detail": "系统可能过载，影响响应时间",
            })
    
    mem_info = linux_res.get("memory", {})
    if mem_info:
        total_mb = mem_info.get("total_mb", 1)
        available_mb = mem_info.get("available_mb", total_mb)
        used_pct = (total_mb - available_mb) / total_mb * 100 if total_mb > 0 else 0
        if used_pct > 90:
            anomalies.append({
                "severity": "high",
                "category": "system_resources",
                "finding": f"内存使用率 {used_pct:.0f}% 超过 90%",
                "detail": "可能触发 OOM，影响 session 和工具执行",
            })
        elif used_pct > 80:
            anomalies.append({
                "severity": "medium",
                "category": "system_resources",
                "finding": f"内存使用率 {used_pct:.0f}% 超过 80%",
                "detail": "建议监控，考虑清理缓存或大 session 文件",
            })
    
    swap_used = mem_info.get("swap_used_mb", 0)
    if swap_used > 100:
        anomalies.append({
            "severity": "medium",
            "category": "system_resources",
            "finding": f"交换分区使用 {swap_used}MB",
            "detail": "内存压力较大，swap 活跃",
        })
    
    zombie = linux_res.get("processes", {}).get("zombie", 0)
    if zombie > 5:
        anomalies.append({
            "severity": "medium",
            "category": "system_resources",
            "finding": f"僵尸进程 {zombie} 个",
            "detail": "可能存在未正确回收的子进程",
        })

    # OpenClaw 架构异常
    openclaw_arch = harness_data.get("openclaw_architecture", {})
    gateway_arch = openclaw_arch.get("gateway", {})
    if not gateway_arch.get("ok", True):
        anomalies.append({
            "severity": "high",
            "category": "openclaw_architecture",
            "finding": "OpenClaw Gateway 未运行",
            "detail": "所有通道和 session 可能中断",
        })
    
    channels = openclaw_arch.get("channels", {})
    for ch_name, ch_status in channels.items():
        if ch_name == "weixin" and not ch_status.get("configured", True):
            anomalies.append({
                "severity": "medium",
                "category": "openclaw_architecture",
                "finding": "微信通道未配置",
                "detail": "微信消息收发可能中断",
            })
        if ch_name == "mail" and not ch_status.get("systemd_active", True):
            anomalies.append({
                "severity": "medium",
                "category": "openclaw_architecture",
                "finding": "邮件 Webhook systemd 未激活",
                "detail": "邮件接收可能中断",
            })

    # 基础设施异常
    infra_data = infra_mod.get("data", {})
    infra_groups = infra_data.get("groups", []) if infra_data else []
    for ig in infra_groups:
        if ig.get("status") == "❌":
            anomalies.append({
                "severity": "high",
                "category": "infrastructure",
                "finding": f"基础设施 {ig['id']} {ig['name']} 不可用",
                "detail": f"检查 {ig['name']} 配置和进程状态",
            })

    # 能力缺失
    if not cap_data.get("github_api"):
        anomalies.append({
            "severity": "medium",
            "category": "capability",
            "finding": "GitHub API 不可用",
            "detail": "影响 bounty 扫描和 PR 提交",
        })

    # 模块失败
    for name, mod in modules_data.items():
        if mod.get("error"):
            anomalies.append({
                "severity": "high",
                "category": "module",
                "finding": f"模块 {name} 运行失败: {mod['error'][:60]}",
                "detail": "数据不完整，建议检查脚本",
            })

    analysis["anomalies"] = anomalies

    # ── 3. 趋势判断 ──
    trends = []

    # 读取上次 baseline 对比
    state_path = f"{WORKSPACE}/skills/p1-0/state.json"
    last_score = None
    if os.path.exists(state_path):
        try:
            with open(state_path, "r") as f:
                old_state = json.load(f)
            last_baseline = old_state.get("last_baseline", {})
            last_score = last_baseline.get("score", {}).get("total")
        except:
            pass

    # 当前计算出的 score（先算出来用于趋势）
    current_score, _ = calculate_score(modules_data)
    if last_score is not None:
        delta = round(current_score - last_score, 1)
        if delta >= 0.5:
            trends.append(f"📈 系统健康度提升 {delta} 分（{last_score} → {current_score}）")
        elif delta <= -0.5:
            trends.append(f"📉 系统健康度下降 {abs(delta)} 分（{last_score} → {current_score}）")
        else:
            trends.append(f"➡️ 系统健康度持平（{current_score} 分）")
    else:
        trends.append(f"🆕 首次 baseline，当前评分 {current_score}")

    # 活跃项目趋势
    total_active = sum(g["stats"]["active"] for g in groups)
    total_projects = sum(g["stats"]["total"] for g in groups)
    if total_projects > 0:
        active_ratio = total_active / total_projects
        if active_ratio >= 0.5:
            trends.append(f"✅ 活跃项目占比 {active_ratio*100:.0f}%，整体可控")
        else:
            trends.append(f"⚠️ 活跃项目仅占 {active_ratio*100:.0f}%，多数项目停滞")

    # 环境趋势
    if disk_pct > 90:
        trends.append("🔴 磁盘逼近满载，近期需紧急清理")
    elif disk_pct > 80:
        trends.append("🟡 磁盘使用率偏高，建议纳入下周清理计划")

    # 环境趋势 - 系统资源
    cpu_load = harness_data.get("linux_resources", {}).get("cpu_load", {})
    if cpu_load:
        load_1min = cpu_load.get("1min", 0)
        cpu_cores = harness_data.get("linux_resources", {}).get("cpu_cores", 1)
        if load_1min > cpu_cores * 1.5:
            trends.append(f"🟡 CPU 负载 {load_1min} 偏高（核心 {cpu_cores}），注意资源竞争")
    
    mem_info = harness_data.get("linux_resources", {}).get("memory", {})
    if mem_info:
        total_mb = mem_info.get("total_mb", 1)
        available_mb = mem_info.get("available_mb", total_mb)
        used_pct = (total_mb - available_mb) / total_mb * 100 if total_mb > 0 else 0
        if used_pct > 85:
            trends.append(f"🟡 内存使用 {used_pct:.0f}%，接近压力阈值")
    
    # OpenClaw 架构趋势
    openclaw_arch = harness_data.get("openclaw_architecture", {})
    gateway_arch = openclaw_arch.get("gateway", {})
    if gateway_arch.get("ok"):
        trends.append("✅ OpenClaw Gateway 运行正常")
    else:
        trends.append("🔴 OpenClaw Gateway 异常，需立即检查")
    
    channels = openclaw_arch.get("channels", {})
    active_channels = sum(1 for ch in channels.values() if ch.get("configured") or ch.get("systemd_active") or ch.get("process_running"))
    total_channels = len(channels)
    if total_channels > 0:
        trends.append(f"📡 通道状态 {active_channels}/{total_channels} 活跃")

    analysis["trends"] = trends

    # ── 4. 改进建议 ──
    recommendations = []

    # 按异常优先级排序建议
    high_anomalies = [a for a in anomalies if a["severity"] == "high"]
    medium_anomalies = [a for a in anomalies if a["severity"] == "medium"]

    for a in high_anomalies[:3]:
        recommendations.append({
            "priority": "immediate",
            "target": a["category"],
            "action": f"处理 {a['finding']} — {a['detail']}",
        })

    for a in medium_anomalies[:3]:
        recommendations.append({
            "priority": "this_cycle",
            "target": a["category"],
            "action": f"跟进 {a['finding']} — {a['detail']}",
        })

    # 通用建议
    if total_active < total_projects:
        stale_names = [p["name"] for g in groups for p in g["projects"] if p["status"] == "stale"]
        if stale_names:
            recommendations.append({
                "priority": "this_cycle",
                "target": "projects",
                "action": f"激活停滞项目: {', '.join(stale_names[:3])}",
            })

    if not mem_data.get("all_key_files_exist"):
        recommendations.append({
            "priority": "immediate",
            "target": "memory",
            "action": "从 git 恢复缺失的关键记忆文件",
        })

    analysis["recommendations"] = recommendations

    # ── 5. 生成 summary 段落 ──
    summary_parts = []
    total_special = len(special_artifacts)
    infra_count = len(infra_groups)
    summary_parts.append(f"本周期扫描到 {total_projects} 个项目分布在 {len(groups)} 个项目群中，另有 {total_special} 个特殊产出物。")
    summary_parts.append(f"系统健康评分 {current_score}/10，")

    if high_anomalies:
        summary_parts.append(f"发现 {len(high_anomalies)} 个严重异常需立即处理。")
    elif medium_anomalies:
        summary_parts.append(f"有 {len(medium_anomalies)} 项中度偏差建议本周期跟进。")
    else:
        summary_parts.append("未发现显著异常，系统运行平稳。")

    # 项目群具体状况
    group_summaries = []
    for g in groups:
        gs = g["group_status"]
        # 特殊产出物统计
        sp_artifacts = g.get("special_artifacts", [])
        sp_count = len(sp_artifacts)
        sp_active = len([a for a in sp_artifacts if a["status"] == "active"])
        if gs == "healthy":
            group_summaries.append(f"{g['tier']} 群健康{'（+' + str(sp_count) + '个产出物）' if sp_count else ''}")
        elif gs == "mixed":
            group_summaries.append(f"{g['tier']} 群部分停滞（{g['stats']['stale']}/{g['stats']['total']}）{'（+' + str(sp_count) + '个产出物）' if sp_count else ''}")
        elif gs == "stale":
            group_summaries.append(f"{g['tier']} 群全面停滞")
        else:
            group_summaries.append(f"{g['tier']} 群有 orphan 项目")
    if group_summaries:
        summary_parts.append("项目群状况: " + "；".join(group_summaries) + "。")
    
    # 基础设施状况
    if infra_count > 0:
        infra_healthy = sum(1 for ig in infra_groups if ig.get("status") == "✅")
        summary_parts.append(f"基础设施 {infra_healthy}/{infra_count} 项健康。")

    analysis["summary"] = "".join(summary_parts)

    return analysis


def generate_gap_matrix(modules_data, expected_state):
    """
    期望 vs 现实 差距矩阵
    读取 P*.json 期望状态 + MEMORY.md 记忆，与扫描现实对比
    """
    projects_mod = modules_data.get("projects", {})
    groups = projects_mod.get("data", {}).get("groups", [])
    flat_projects = projects_mod.get("data", {}).get("flat_projects", [])

    matrix = []
    file_expectations = expected_state.get("files", {})
    memory_hints = expected_state.get("memory_hints", {})

    tier_defs = {
        "P0": {"name": "P0: GitHub 赚钱任务", "fallback_goal": "通过 GitHub / bounty 获取收入"},
        "P1": {"name": "P1: 自进化任务", "fallback_goal": "自学习循环、Skill 进化"},
        "P2": {"name": "P2: 社交网络探索", "fallback_goal": "Agent 社区互动"},
        "P3": {"name": "P3: 用户安排的其它任务", "fallback_goal": "用户指派任务"},
    }

    for tier, td in tier_defs.items():
        exp = file_expectations.get(tier, {})
        group = next((g for g in groups if g["tier"] == tier), None)

        # 期望状态描述
        expected_desc = ""
        if exp.get("error"):
            expected_desc = f"期望文件读取失败: {exp['error']}"
        elif exp:
            step = exp.get("current_step") or "未记录"
            last_action = exp.get("last_action", "")[:60]
            blocker = exp.get("blocker")
            next_steps = exp.get("next_steps", [])
            expected_desc = f"当前阶段: {step}"
            if last_action:
                expected_desc += f" | 最近动作: {last_action}"
            if next_steps:
                expected_desc += f" | 下一步: {next_steps[0]}"
            if blocker:
                expected_desc += f" | 🔴 blocker: {blocker}"
        else:
            expected_desc = memory_hints.get(tier, "未记录期望")

        # 现实状态描述
        if group:
            stats = group["stats"]
            stale_names = [p["name"] for p in group["projects"] if p["status"] == "stale"]
            active_names = [p["name"] for p in group["projects"] if p["status"] == "active"]
            reality_desc = f"{stats['active']}/{stats['total']} 活跃"
            if stale_names:
                reality_desc += f" | 停滞: {', '.join(stale_names)}"
            if active_names:
                reality_desc += f" | 活跃: {', '.join(active_names)}"
        else:
            # 检查是否有未分组的该项目
            orphan = [p for p in flat_projects if p["name"].startswith(tier.lower())]
            if orphan:
                reality_desc = f"有 {len(orphan)} 个项目但未归类到 {tier}"
            else:
                reality_desc = "无项目"

        # 差距判断
        gap_level = "✅ 符合"
        gap_reason = ""
        suggestion = "维持现状"

        if not group and not orphan:
            gap_level = "⚪ 未启动"
            gap_reason = "项目群为空"
            suggestion = f"启动 {td['fallback_goal']}"
        elif group:
            stats = group["stats"]
            if stats["total"] > 0 and stats["active"] == 0:
                gap_level = "🔴 严重偏差"
                gap_reason = "全部项目停滞"
                suggestion = f"检查 blocker，激活 {tier} 任务"
            elif stats["stale"] > 0 and stats["active"] > 0:
                gap_level = "🟡 偏差"
                gap_reason = f"{stats['stale']}/{stats['total']} 项目停滞"
                # 检查期望中是否有 blocker
                if exp and exp.get("blocker"):
                    suggestion = f"blocker: {exp['blocker']}，需浩然介入或重新规划"
                else:
                    oldest_stale = max(
                        [p for p in group["projects"] if p["status"] == "stale"],
                        key=lambda x: x["age_hours"],
                        default=None
                    )
                    if oldest_stale and oldest_stale["age_hours"] > 48:
                        suggestion = f"{oldest_stale['name']} 已停滞 {oldest_stale['age_hours']:.0f}h，检查 blocker 或推进 next action"
                    else:
                        suggestion = "推进 next action，激活停滞项目"
            elif exp and exp.get("blocker"):
                gap_level = "🔴 严重偏差"
                gap_reason = f"期望中记录 blocker: {exp['blocker']}"
                suggestion = "解除 blocker 是首要任务"
            elif stats["active"] == stats["total"]:
                gap_level = "✅ 符合"
                gap_reason = "所有项目活跃"
                suggestion = "维持节奏，考虑扩展"

        matrix.append({
            "tier": tier,
            "tier_name": td["name"],
            "expected": expected_desc,
            "reality": reality_desc,
            "gap": gap_level,
            "gap_reason": gap_reason,
            "suggestion": suggestion,
        })

    return matrix


def calculate_score(modules_data):
    """计算系统健康分
    项目30% + 环境20% + 记忆20% + 能力20% + 趋势10%
    """
    score = 0
    breakdown = {}

    # 项目健康 (30%) — 基于项目群加权平均
    projects_mod = modules_data.get("projects", {})
    groups = projects_mod.get("data", {}).get("groups", [])
    flat_projects = projects_mod.get("data", {}).get("flat_projects", [])

    if groups:
        # 项目群级别加权：按项目数加权平均
        total_weight = sum(g["stats"]["total"] for g in groups)
        if total_weight > 0:
            project_score = sum(
                g.get("group_score", 0) * (g["stats"]["total"] / total_weight)
                for g in groups
            )
        else:
            project_score = 5
    elif flat_projects:
        active = len([p for p in flat_projects if p.get("status") == "active"])
        total = len(flat_projects)
        project_score = min(10, (active / total) * 10) if total > 0 else 5
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

    # 历史趋势 (10%) — 基于上次对比，默认 5
    trend_score = 5
    breakdown["trend"] = trend_score
    score += trend_score * 0.10

    return round(score, 1), breakdown


def generate_alerts(modules_data):
    """从模块数据生成告警清单"""
    alerts = []

    # 项目群级别告警
    projects_mod = modules_data.get("projects", {})
    groups = projects_mod.get("data", {}).get("groups", [])
    for g in groups:
        if g.get("group_status") == "stale":
            alerts.append({
                "level": "critical",
                "category": "project_group",
                "item": f"{g['name']} 全面停滞 ({g['stats']['stale']}/{g['stats']['total']} 项目 stale)",
                "suggestion": f"检查 {g['tier']} 项目群的 blocker，优先激活",
            })
        elif g.get("group_status") == "mixed":
            stale_names = [p["name"] for p in g["projects"] if p["status"] == "stale"]
            alerts.append({
                "level": "warning",
                "category": "project_group",
                "item": f"{g['name']} 部分停滞: {', '.join(stale_names)}",
                "suggestion": f"推进 {g['tier']} 停滞项目的 next action",
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

    # 基础设施告警
    infra_mod = modules_data.get("infrastructure", {})
    infra_data = infra_mod.get("data", {})
    infra_groups = infra_data.get("groups", [])
    for ig in infra_groups:
        if ig.get("status") == "❌":
            alerts.append({
                "level": "critical",
                "category": "infrastructure",
                "item": f"{ig['id']} {ig['name']} 不可用",
                "suggestion": f"检查 {ig['name']} 配置和进程",
            })

    # 排序
    level_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: level_order.get(x["level"], 99))

    return alerts


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(f"{REPORTS_DIR}/history", exist_ok=True)

    print("🔍 P1.0 baseline-check orchestrator v3 启动...", file=sys.stderr)

    # 发现所有模块
    module_scripts = sorted(glob.glob(f"{MODULES_DIR}/check-*.py"))
    print(f"  → 发现 {len(module_scripts)} 个检查模块", file=sys.stderr)

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
                    print(f"  ⚠️ {key}: {error}", file=sys.stderr)
                else:
                    passed = result.get("checks_passed", 0)
                    total = result.get("checks_total", 0)
                    print(f"  ✅ {key}: {passed}/{total} 通过", file=sys.stderr)
            except Exception as e:
                print(f"  ❌ {module_name}: {e}", file=sys.stderr)
                modules_data[module_name] = {"module": module_name, "error": str(e), "checks_passed": 0, "checks_total": 0}

    print("🧠 执行 AI 分析...", file=sys.stderr)
    ai_analysis = perform_ai_analysis(modules_data)

    # ── 期望 vs 现实 ──
    print("📋 生成期望 vs 现实差距矩阵...", file=sys.stderr)
    expected_state = load_expected_state()
    gap_matrix = generate_gap_matrix(modules_data, expected_state)

    # 计算评分
    print("📊 计算评分...", file=sys.stderr)
    score, breakdown = calculate_score(modules_data)
    alerts = generate_alerts(modules_data)

    # 组装统一报告
    report = {
        "meta": {
            "version": "p1-baseline-v4-ai-gap-infra",
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
        "ai_analysis": ai_analysis,
        "gap_matrix": gap_matrix,
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
    print(f"  → JSON: {json_path}", file=sys.stderr)

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

    # 输出摘要（到 stderr，避免污染 JSON 输出）
    summary_text = f"""
{'='*60}
✅ P1.0 检查完成
{'='*60}
评分：{score}/10（{report['score']['grade']} 级）
模块：{report['meta']['modules_ok']}/{report['meta']['modules_run']} 成功
告警：🔴 {report['alert_count']['critical']} 🟡 {report['alert_count']['warning']} 🟢 {report['alert_count']['info']}
AI 摘要：{ai_analysis['summary'][:120]}...
差距矩阵：{len(gap_matrix)} 个项目群已对比
{'='*60}
"""
    print(summary_text, file=sys.stderr)

    # 只输出 JSON 到 stdout
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    main()
