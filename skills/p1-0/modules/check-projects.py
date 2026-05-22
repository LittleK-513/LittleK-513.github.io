#!/usr/bin/env python3
"""check-projects.py — 项目审计模块（五层项目群结构 + 特殊产出物识别）
独立运行输出 JSON：python3 check-projects.py
输出格式：{"module": "projects", "data": {"groups": [...]}, ...}
"""

import os, json, time, glob
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"

EXCLUDE_DIRS = {
    "node_modules", "tmp", ".local", "blog", "downloads", "__pycache__",
    "backups", "daily", "data", "memorized_diary", "memorized_media",
    "memory", "references", "skills", "todo", "weekly", ".openclaw",
    "memory_consolidation", "orchestrator-runs", "self-evolution", "state",
    "dashboard", "projects", "scripts",
}

# 五层项目群定义：name_pattern → tier
TIER_MAP = {
    # P0: GitHub 赚钱任务
    "bounty": {"tier": "P0", "group_name": "P0: GitHub 赚钱任务", "group_goal": "通过 GitHub issue、bounty 平台获取收入"},
    "p0-github-money": {"tier": "P0", "group_name": "P0: GitHub 赚钱任务", "group_goal": "通过 GitHub issue、bounty 平台获取收入"},
    "p0-": {"tier": "P0", "group_name": "P0: GitHub 赚钱任务", "group_goal": "通过 GitHub issue、bounty 平台获取收入"},
    # P1: 自进化任务
    "p1-self-evolution": {"tier": "P1", "group_name": "P1: 自进化任务", "group_goal": "自学习、自改进、Skill 进化与系统能力增强"},
    "hermes-lite": {"tier": "P1", "group_name": "P1: 自进化任务", "group_goal": "自学习、自改进、Skill 进化与系统能力增强"},
    "p1-": {"tier": "P1", "group_name": "P1: 自进化任务", "group_goal": "自学习、自改进、Skill 进化与系统能力增强"},
    # P2: 社交网络探索
    "p2-agent-social": {"tier": "P2", "group_name": "P2: 社交网络探索", "group_goal": "Agent 社交网络互动、社区建立与影响力扩展"},
    "p2-moltbook": {"tier": "P2", "group_name": "P2: 社交网络探索", "group_goal": "Agent 社交网络互动、社区建立与影响力扩展"},
    "p2-": {"tier": "P2", "group_name": "P2: 社交网络探索", "group_goal": "Agent 社交网络互动、社区建立与影响力扩展"},
    # P3: 用户安排的其它任务
    "p3-": {"tier": "P3", "group_name": "P3: 用户安排的其它任务", "group_goal": "用户直接指派的外部任务与探索"},
}


def detect_tier(name):
    """根据项目名称检测所属项目群"""
    # 完全匹配优先
    if name in TIER_MAP:
        return TIER_MAP[name]
    # 前缀匹配
    for prefix, info in TIER_MAP.items():
        if name.startswith(prefix):
            return info
    # 尝试从 state.json 中的 tier 字段推断
    return {"tier": None, "group_name": "未分类", "group_goal": "未归类到任何项目群"}


def scan_single_project(name, path):
    """扫描单个项目目录，返回项目详情字典"""
    has_state = os.path.exists(f"{path}/state.json")
    has_readme = os.path.exists(f"{path}/README.md") or os.path.exists(f"{path}/readme.md")
    has_project_py = os.path.exists(f"{path}/project-status.py")
    has_todo = os.path.exists(f"{path}/todo") and os.path.isdir(f"{path}/todo")

    state_info = None
    tier_from_state = None
    last_updated = None
    blocker = None
    last_action = None

    if has_state:
        try:
            with open(f"{path}/state.json", "r") as f:
                state_info = json.load(f)
            tier_from_state = state_info.get("tier") or state_info.get("p0_id") or state_info.get("tier_id")
            if tier_from_state == "github-money":
                tier_from_state = "P0"
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

    return {
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
        "blocker": blocker,
        "last_action": str(last_action)[:200] if last_action else None,
        "state_tier": tier_from_state,
    }


def discover_special_artifacts():
    """
    扫描 workspace 根目录的特殊文件/目录，映射到项目群。
    返回统一的项目结构列表（name, tier, group, status, last_modified, details）
    """
    artifacts = []
    now = time.time()

    # ── P1 自进化 内部子项目 ──
    p1_artifacts = [
        {
            "name": "P1.1 日记系统",
            "path": f"{WORKSPACE}/diary",
            "check_path": f"{WORKSPACE}/diary",
            "tier": "P1",
            "group": "P1 自进化内部",
            "details": "每日内观与觉察记录",
        },
        {
            "name": "P1.2 学习积累",
            "path": f"{WORKSPACE}/diary/LEARNINGS.md",
            "check_path": f"{WORKSPACE}/diary/LEARNINGS.md",
            "tier": "P1",
            "group": "P1 自进化内部",
            "details": "经验沉淀与教训记录",
        },
        {
            "name": "P1.3 资源感知舱",
            "path": "/root/.openclaw/scripts/resource-tracker.py",
            "check_path": "/root/.openclaw/scripts/resource-tracker.py",
            "tier": "P1",
            "group": "P1 自进化内部",
            "details": "系统资源采集与监控",
        },
        {
            "name": "P1.4 心跳/内观机制",
            "path": "/root/.openclaw/scripts/momentum-trigger.sh",
            "check_path": "/root/.openclaw/scripts/momentum-trigger.sh",
            "tier": "P1",
            "group": "P1 自进化内部",
            "details": "长期任务 idle 检查与触发",
        },
        {
            "name": "P1.5 Session 管理",
            "path": f"{WORKSPACE}/scripts/session-cleanup.sh",
            "check_path": f"{WORKSPACE}/scripts/session-cleanup.sh",
            "tier": "P1",
            "group": "P1 自进化内部",
            "details": "Session 清理与归档",
        },
        {
            "name": "P1.6 网站 (littlek-513.github.io)",
            "path": f"{WORKSPACE}/index.html",
            "check_path": f"{WORKSPACE}/index.html",
            "tier": "P1",
            "group": "P1 自进化内部",
            "details": "Jekyll 静态站点 + Dashboard 主页",
            "extra_paths": [f"{WORKSPACE}/_layouts", f"{WORKSPACE}/_posts"],
        },
    ]

    # ── P3 用户安排的其它任务 ──
    p3_artifacts = [
        {
            "name": "P3.1 SpaceX S-1 分析",
            "path": f"{WORKSPACE}/spacex-s1",
            "check_path": f"{WORKSPACE}/spacex-s1",
            "tier": "P3",
            "group": "P3 用户任务",
            "details": "SpaceX S-1 财务与运营分析",
        },
        {
            "name": "P3.2 CFMS 数据抓取",
            "path": f"{WORKSPACE}/data.jsonl",
            "check_path": f"{WORKSPACE}/data.jsonl",
            "tier": "P3",
            "group": "P3 用户任务",
            "details": "CFM 发动机数据抓取与备份",
            "extra_paths": [f"{WORKSPACE}/cfm_backup.py", f"{WORKSPACE}/cfm_scraper.py"],
        },
        {
            "name": "P3.3 创始人手册翻译",
            "path": f"{WORKSPACE}/founders-handbook.md",
            "check_path": f"{WORKSPACE}/founders-handbook.md",
            "tier": "P3",
            "group": "P3 用户任务",
            "details": "YC 创始人手册中文翻译",
        },
        {
            "name": "P3.4 Claude 桥接",
            "path": f"{WORKSPACE}/claude-openclaw-bridge.md",
            "check_path": f"{WORKSPACE}/claude-openclaw-bridge.md",
            "tier": "P3",
            "group": "P3 用户任务",
            "details": "Claude 与 OpenClaw 桥接方案",
        },
        {
            "name": "P3.5 Mac 连接通道",
            "path": f"{WORKSPACE}/mac-bridge-websocket-spec.md",
            "check_path": f"{WORKSPACE}/mac-bridge-websocket-spec.md",
            "tier": "P3",
            "group": "P3 用户任务",
            "details": "Mac 桥接 WebSocket 规格",
        },
    ]

    all_specs = p1_artifacts + p3_artifacts

    for spec in all_specs:
        check_path = spec["check_path"]
        exists = os.path.exists(check_path)

        # 计算最后修改时间和文件数
        latest_mtime = 0
        file_count = 0
        if exists:
            if os.path.isfile(check_path):
                latest_mtime = os.path.getmtime(check_path)
                file_count = 1
            elif os.path.isdir(check_path):
                for root, dirs, files_inner in os.walk(check_path):
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    file_count += len(files_inner)
                    for f in files_inner:
                        try:
                            mtime = os.path.getmtime(os.path.join(root, f))
                            if mtime > latest_mtime:
                                latest_mtime = mtime
                        except:
                            pass

            # 检查 extra_paths
            for extra in spec.get("extra_paths", []):
                if os.path.exists(extra):
                    if os.path.isfile(extra):
                        file_count += 1
                        mtime = os.path.getmtime(extra)
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                    elif os.path.isdir(extra):
                        for root, dirs, files_inner in os.walk(extra):
                            dirs[:] = [d for d in dirs if not d.startswith(".")]
                            file_count += len(files_inner)
                            for f in files_inner:
                                try:
                                    mtime = os.path.getmtime(os.path.join(root, f))
                                    if mtime > latest_mtime:
                                        latest_mtime = mtime
                                except:
                                    pass

        age_hours = (now - latest_mtime) / 3600 if latest_mtime else float("inf")

        if not exists and not file_count:
            status = "ghost"
        elif age_hours < 168:
            status = "active"
        else:
            status = "stale"

        artifacts.append({
            "name": spec["name"],
            "path": spec["path"],
            "tier": spec["tier"],
            "group": spec["group"],
            "status": status,
            "exists": exists,
            "file_count": file_count,
            "last_modified": datetime.fromtimestamp(latest_mtime).isoformat() if latest_mtime else None,
            "age_hours": round(age_hours, 1),
            "details": spec["details"],
            "blocker": None,
            "last_action": None,
            "is_special_artifact": True,
        })

    return artifacts


def check():
    checks_passed = 0
    checks_total = 2

    # 收集所有候选目录
    candidates = []
    for item in os.listdir(WORKSPACE):
        item_path = os.path.join(WORKSPACE, item)
        if not os.path.isdir(item_path):
            continue
        if item.startswith(".") or item in EXCLUDE_DIRS:
            continue
        candidates.append((item, item_path))

    # projects/ 子目录
    projects_dir = f"{WORKSPACE}/projects"
    if os.path.exists(projects_dir):
        for sub in os.listdir(projects_dir):
            sub_path = os.path.join(projects_dir, sub)
            if os.path.isdir(sub_path) and not sub.startswith(".") and sub not in EXCLUDE_DIRS:
                candidates.append((sub, sub_path))

    # 去重扫描
    seen = set()
    all_projects = []
    for name, path in candidates:
        if name in seen:
            continue
        seen.add(name)

        # 排除非项目目录
        try:
            files = os.listdir(path)
            is_empty = len(files) == 0
            only_hidden = all(f.startswith(".") for f in files)
        except:
            continue

        # 判定是否为项目：有 state.json / README / project-status.py / todo / tiered 前缀
        has_state = os.path.exists(f"{path}/state.json")
        has_readme = os.path.exists(f"{path}/README.md") or os.path.exists(f"{path}/readme.md")
        has_project_py = os.path.exists(f"{path}/project-status.py")
        has_todo = os.path.exists(f"{path}/todo") and os.path.isdir(f"{path}/todo")
        is_tiered = name.startswith(("p0-", "p1-", "p2-", "p3-"))
        is_project = has_state or has_project_py or (has_readme and has_todo) or is_tiered

        if is_empty or only_hidden or not is_project:
            continue

        proj = scan_single_project(name, path)
        all_projects.append(proj)

    # 获取特殊产出物
    special_artifacts = discover_special_artifacts()

    # 按 tier 分组（目录项目 + 特殊产出物）
    groups = []
    tier_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    tiers_found = set()

    for proj in all_projects:
        tier_info = detect_tier(proj["name"])
        proj["tier"] = tier_info["tier"] or proj.get("state_tier")
        tiers_found.add(proj["tier"])

    # 按预设顺序创建组（包含特殊产出物）
    tier_defs = [
        {"tier": "P0", "name": "P0: GitHub 赚钱任务", "goal": "通过 GitHub issue、bounty 平台获取收入"},
        {"tier": "P1", "name": "P1: 自进化任务", "goal": "自学习、自改进、Skill 进化与系统能力增强"},
        {"tier": "P2", "name": "P2: 社交网络探索", "goal": "Agent 社交网络互动、社区建立与影响力扩展"},
        {"tier": "P3", "name": "P3: 用户安排的其它任务", "goal": "用户直接指派的外部任务与探索"},
    ]

    for td in tier_defs:
        # 目录项目
        tier_projects = [p for p in all_projects if p["tier"] == td["tier"]]
        # 特殊产出物
        tier_artifacts = [a for a in special_artifacts if a["tier"] == td["tier"]]

        if not tier_projects and not tier_artifacts:
            continue

        # 组内排序
        tier_projects.sort(key=lambda x: x["name"])

        # 合并统计
        all_items = tier_projects + tier_artifacts
        active_count = len([p for p in all_items if p["status"] == "active"])
        stale_count = len([p for p in all_items if p["status"] == "stale"])
        orphan_count = len([p for p in all_items if p["status"] == "orphan"])
        ghost_count = len([p for p in all_items if p["status"] == "ghost"])
        total = len(all_items)

        # 项目群健康度评分 (0-10)
        if total > 0:
            group_score = (active_count / total) * 10
            if stale_count > 0:
                group_score -= (stale_count / total) * 3
            if ghost_count > 0:
                group_score -= 1
            group_score = max(0, round(group_score, 1))
        else:
            group_score = 0

        # 项目群整体状态
        if active_count == total:
            group_status = "healthy"
        elif stale_count > 0 and active_count > 0:
            group_status = "mixed"
        elif stale_count > 0:
            group_status = "stale"
        elif orphan_count > 0:
            group_status = "orphan"
        else:
            group_status = "empty"

        groups.append({
            "tier": td["tier"],
            "name": td["name"],
            "goal": td["goal"],
            "projects": tier_projects,
            "special_artifacts": tier_artifacts,
            "stats": {
                "total": total,
                "active": active_count,
                "stale": stale_count,
                "orphan": orphan_count,
                "ghost": ghost_count,
            },
            "group_score": group_score,
            "group_status": group_status,
            "group_health": "🟢 健康" if group_status == "healthy" else (
                "🟡 部分停滞" if group_status == "mixed" else (
                "🟠 全面停滞" if group_status == "stale" else "⚪ 空群"
            )),
        })

    # 全局统计
    all_active = sum(g["stats"]["active"] for g in groups)
    all_stale = sum(g["stats"]["stale"] for g in groups)
    all_orphan = sum(g["stats"]["orphan"] for g in groups)
    all_ghost = sum(g["stats"]["ghost"] for g in groups)
    all_total = all_active + all_stale + all_orphan + all_ghost

    if all_total > 0:
        checks_passed = (1 if all_active >= 1 else 0) + (1 if all_total >= 1 else 0)

    data = {
        "groups": groups,
        "flat_projects": all_projects,
        "special_artifacts": special_artifacts,
        "active_count": all_active,
        "stale_count": all_stale,
        "orphan_count": all_orphan,
        "ghost_count": all_ghost,
        "total_count": all_total,
    }

    return {"module": "projects", "data": data, "checks_passed": checks_passed, "checks_total": checks_total}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, ensure_ascii=False))
