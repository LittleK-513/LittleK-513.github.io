#!/usr/bin/env python3
"""generate-report.py — P1.0 baseline-check 报告生成器 v3
输入：orchestrator 输出的统一 JSON（stdin 或文件）
输出：
  1. reports/p1-0/latest.json  — 完整数据包
  2. reports/p1-0/latest.md     — Markdown 人类可读报告
  3. p1-dashboard.html          — HTML 可视化仪表板（四层树 + AI 分析 + 差距矩阵）
用法：
  python3 orchestrator.py | python3 generate-report.py
  或：python3 generate-report.py < reports/p1-0/latest.json
"""

import os, sys, json, glob
from datetime import datetime

WORKSPACE = "/root/.openclaw/workspace"
REPORTS_DIR = f"{WORKSPACE}/reports/p1-0"
SKILL_DIR = f"{WORKSPACE}/skills/p1-0"
MODULES_DIR = f"{SKILL_DIR}/modules"


def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def get_skill_sources():
    """读取所有 Skill 源码文件"""
    sources = []
    
    doc_path = f"{SKILL_DIR}/baseline-check-v2.md"
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            sources.append(("baseline-check-v2.md", f.read()))
    except Exception as e:
        sources.append(("baseline-check-v2.md", f"# 读取失败: {e}"))
    
    orch_path = f"{SKILL_DIR}/orchestrator.py"
    try:
        with open(orch_path, "r", encoding="utf-8") as f:
            sources.append(("orchestrator.py", f.read()))
    except Exception as e:
        sources.append(("orchestrator.py", f"# 读取失败: {e}"))
    
    for script_path in sorted(glob.glob(f"{MODULES_DIR}/check-*.py")):
        name = os.path.basename(script_path)
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                sources.append((name, f.read()))
        except Exception as e:
            sources.append((name, f"# 读取失败: {e}"))
    
    return sources


def generate_markdown(report):
    meta = report["meta"]
    score = report["score"]
    modules = report["modules"]
    alerts = report["alerts"]
    ai_analysis = report.get("ai_analysis", {})
    gap_matrix = report.get("gap_matrix", [])
    
    model = modules.get("model", {}).get("data", {})
    env = modules.get("environment", {}).get("data", {})
    harness = modules.get("harness", {}).get("data", {})
    memory = modules.get("memory", {}).get("data", {})
    projects = modules.get("projects", {}).get("data", {})
    cap = modules.get("capabilities", {}).get("data", {})
    sessions = modules.get("sessions", {}).get("data", {})
    git = env.get("git", {})
    groups = projects.get("groups", [])
    
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
        w = float(weights.get(dim, "0").rstrip("%")) / 100
        md += f"| {dim} | {val} | {weights.get(dim, '-')} | {round(val * w, 2)} |\n"
    
    md += f"""
---

## AI 分析摘要

{ai_analysis.get('summary', '暂无分析')}

### 健康度评估
"""
    for tier, ha in ai_analysis.get("health_assessment", {}).items():
        md += f"- **{tier}**: 评分 {ha.get('score', '-')}/10，状态 {ha.get('status', '-')}\n"
        for note in ha.get("notes", []):
            md += f"  - {note}\n"
    
    md += f"""
### 趋势判断
"""
    for t in ai_analysis.get("trends", []):
        md += f"- {t}\n"
    
    md += f"""
### 改进建议
"""
    for rec in ai_analysis.get("recommendations", [])[:5]:
        icon = "🔴" if rec.get("priority") == "immediate" else "🟡"
        md += f"- {icon} **{rec.get('target', '-')}**: {rec.get('action', '')}\n"
    
    md += f"""
---

## 期望 vs 现实 差距矩阵

| 项目群 | 期望状态 | 扫描现实 | 差距 | 改进建议 |
|--------|----------|----------|------|----------|
"""
    for row in gap_matrix:
        md += f"| {row['tier']} | {row['expected'][:60]}… | {row['reality'][:40]}… | {row['gap']} | {row['suggestion'][:50]}… |\n"
    
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
| Gateway | {harness.get('gateway_status', 'unknown')[:20]}... |
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

## 项目审计（四层结构）

"""
    for g in groups:
        md += f"""### {g['name']} [{g['tier']}]

> 目标：{g['goal']}  
> 健康：{g['group_health']} | 评分：{g['group_score']}/10

| 项目 | 状态 | 文件数 | 最后活跃 | Blocker | 最近动作 |
|------|------|--------|----------|---------|----------|
"""
        for p in g.get("projects", []):
            status_icon = "🟢" if p["status"] == "active" else ("🟡" if p["status"] == "stale" else "⚪")
            blocker = (p.get("blocker") or "-")[:30]
            action = (p.get("last_action") or "-")[:40]
            md += f"| {p['name']} | {status_icon} {p['status']} | {p['file_count']} | {p['age_hours']:.0f}h | {blocker} | {action} |\n"
        md += "\n"
    
    md += f"""---

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

最近会话：{sessions.get('total_sessions', 0)} 个文件

"""
    for s in sessions.get("recent_10", [])[:5]:
        md += f"- `{s['file']}` ({s['size']}, {s['age_hours']:.0f}h ago)\n"
    
    md += """
---

## 模块运行状态

| 模块 | 检查通过 | 总计 | 状态 |
|------|---------|------|------|
"""
    for name, mod in modules.items():
        err = mod.get("error")
        passed = mod.get("checks_passed", 0)
        total = mod.get("checks_total", 0)
        status = f"❌ {err[:30]}" if err else f"✅ {passed}/{total}"
        md += f"| {name} | {passed} | {total} | {status} |\n"
    
    md += """
---

*报告由 P1.0 baseline-check Skill 自动生成*
"""
    return md


def escape_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_html(report):
    score = report["score"]
    modules = report["modules"]
    alerts = report["alerts"]
    ai_analysis = report.get("ai_analysis", {})
    gap_matrix = report.get("gap_matrix", [])
    
    env = modules.get("environment", {}).get("data", {})
    harness = modules.get("harness", {}).get("data", {})
    memory = modules.get("memory", {}).get("data", {})
    projects_data = modules.get("projects", {}).get("data", {})
    cap = modules.get("capabilities", {}).get("data", {})
    sessions = modules.get("sessions", {}).get("data", {})
    git = env.get("git", {})
    groups = projects_data.get("groups", [])
    
    critical = len([a for a in alerts if a["level"] == "critical"])
    warning = len([a for a in alerts if a["level"] == "warning"])
    info = len([a for a in alerts if a["level"] == "info"])
    
    score_data_json = json.dumps(score["breakdown"], ensure_ascii=False)
    
    # Skill 源码章节
    skill_sources = get_skill_sources()
    skill_sections = []
    for fname, content in skill_sources:
        escaped = escape_html(content)
        skill_sections.append(f"""  <details style="margin-top: 1rem;">
    <summary style="cursor: pointer; color: var(--accent); margin-bottom: 0.5rem;">
      {'📄' if fname.endswith('.md') else '🐍'} {fname}
    </summary>
    <pre style="margin-top: 0.5rem; padding: 1rem; background: #0a0a0f; border-radius: 8px; overflow-x: auto; font-size: 0.75rem; color: var(--text-dim); max-height: 400px; overflow-y: auto;"><code>{escaped}</code></pre>
  </details>""")
    
    alerts_html = "".join([
        f'<div class="alert-item alert-{a["level"]}">'
        f'<strong>{"🔴" if a["level"]=="critical" else ("🟡" if a["level"]=="warning" else "🟢")} [{a["level"].upper()}]</strong> '
        f'<span style="color: var(--text-dim);">[{a["category"]}]</span> {a["item"]}<br>'
        f'<span style="color: var(--accent-dim); font-size: 0.85rem;">→ {a["suggestion"]}</span>'
        f'</div>'
        for a in alerts
    ]) if alerts else '<p style="color: var(--good); text-align: center; padding: 1rem;">✅ 无告警</p>'
    
    # 四层项目树形展示
    tier_tree_html = ""
    for g in groups:
        tier = g["tier"]
        stats = g["stats"]
        health_color = "var(--good)" if g["group_status"] == "healthy" else ("var(--warn)" if g["group_status"] == "mixed" else "var(--bad)")
        
        proj_rows = ""
        for p in g.get("projects", []):
            status_class = "badge-good" if p["status"] == "active" else ("badge-warn" if p["status"] == "stale" else "badge-info")
            proj_rows += f"""
          <div class="project-row">
            <span class="project-name">{p['name']}</span>
            <span class="status-badge {status_class}">{p['status']}</span>
            <span class="project-meta">{p['file_count']} 文件 · {p['age_hours']:.0f}h</span>
          </div>"""
        
        tier_tree_html += f"""
      <div class="tier-card">
        <div class="tier-header">
          <span class="tier-badge" style="background: {health_color}20; color: {health_color}; border-color: {health_color};">{tier}</span>
          <span class="tier-title">{g['name'].split(': ', 1)[1]}</span>
          <span class="tier-score">{g['group_score']}/10</span>
        </div>
        <div class="tier-goal">{g['goal']}</div>
        <div class="tier-stats">
          <span class="stat-pill">🟢 {stats['active']} 活跃</span>
          <span class="stat-pill">🟡 {stats['stale']} 停滞</span>
          <span class="stat-pill">⚪ {stats['orphan']} orphan</span>
          <span class="stat-pill">共 {stats['total']}</span>
        </div>
        <div class="tier-projects">
{proj_rows}
        </div>
      </div>"""
    
    # AI 分析摘要 HTML
    ai_summary = escape_html(ai_analysis.get("summary", "暂无分析"))
    
    health_cards = ""
    for tier, ha in ai_analysis.get("health_assessment", {}).items():
        score_val = ha.get("score", 0)
        status = ha.get("status", "unknown")
        color = "var(--good)" if score_val >= 7 else ("var(--warn)" if score_val >= 4 else "var(--bad)")
        notes_html = "<br>".join(escape_html(n) for n in ha.get("notes", []))
        health_cards += f"""
        <div class="health-card">
          <div class="health-tier">{tier}</div>
          <div class="health-score" style="color: {color};">{score_val}/10</div>
          <div class="health-status">{status}</div>
          <div class="health-notes">{notes_html}</div>
        </div>"""
    
    trends_html = ""
    for t in ai_analysis.get("trends", []):
        trends_html += f'<div class="trend-item">{escape_html(t)}</div>\n'
    
    recs_html = ""
    for rec in ai_analysis.get("recommendations", [])[:5]:
        icon = "🔴" if rec.get("priority") == "immediate" else "🟡"
        recs_html += f'<div class="rec-item">{icon} <strong>{rec.get("target", "-")}</strong>: {escape_html(rec.get("action", ""))}</div>\n'
    
    # 差距矩阵 HTML
    gap_rows = ""
    for row in gap_matrix:
        gap_color = "var(--good)" if "✅" in row["gap"] else ("var(--warn)" if "🟡" in row["gap"] else ("var(--bad)" if "🔴" in row["gap"] else "var(--text-dim)"))
        gap_rows += f"""
        <tr>
          <td><strong>{row['tier']}</strong><br><span style="font-size:0.75rem;color:var(--text-dim);">{row['tier_name'].split(': ',1)[1]}</span></td>
          <td style="font-size:0.8rem;">{escape_html(row['expected'][:100])}{'...' if len(row['expected']) > 100 else ''}</td>
          <td style="font-size:0.8rem;">{escape_html(row['reality'][:80])}{'...' if len(row['reality']) > 80 else ''}</td>
          <td style="color: {gap_color}; font-weight: 600;">{row['gap']}</td>
          <td style="font-size:0.8rem;">{escape_html(row['suggestion'][:80])}{'...' if len(row['suggestion']) > 80 else ''}</td>
        </tr>"""
    
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
  margin-bottom: 1.5rem;
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

/* 四层项目树 */
.tier-card {{
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1rem;
}}
.tier-header {{
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}}
.tier-badge {{
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid;
}}
.tier-title {{
  font-size: 1rem;
  font-weight: 500;
  flex: 1;
}}
.tier-score {{
  font-family: monospace;
  color: var(--accent);
}}
.tier-goal {{
  font-size: 0.8rem;
  color: var(--text-dim);
  margin-bottom: 0.5rem;
}}
.tier-stats {{
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}}
.stat-pill {{
  font-size: 0.7rem;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  background: rgba(255,255,255,0.05);
  color: var(--text-dim);
}}
.tier-projects {{
  padding-left: 1rem;
  border-left: 2px solid var(--border);
}}
.project-row {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0;
}}
.project-name {{
  font-family: monospace;
  font-size: 0.85rem;
  min-width: 140px;
}}
.project-meta {{
  font-size: 0.7rem;
  color: var(--text-dim);
  margin-left: auto;
}}

/* AI 分析 */
.ai-summary {{
  background: rgba(0,212,255,0.05);
  border: 1px solid rgba(0,212,255,0.2);
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1rem;
  font-size: 0.95rem;
  line-height: 1.8;
}}
.health-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin: 1rem 0;
}}
.health-card {{
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
}}
.health-tier {{
  font-size: 0.8rem;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 0.3rem;
}}
.health-score {{
  font-size: 1.5rem;
  font-weight: 300;
  margin-bottom: 0.3rem;
}}
.health-status {{
  font-size: 0.75rem;
  color: var(--text-dim);
  margin-bottom: 0.5rem;
}}
.health-notes {{
  font-size: 0.75rem;
  color: var(--text-dim);
  line-height: 1.6;
}}
.trend-item {{
  padding: 0.4rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  font-size: 0.85rem;
}}
.rec-item {{
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  font-size: 0.85rem;
}}

/* 差距矩阵 */
.gap-matrix table {{
  font-size: 0.8rem;
}}
.gap-matrix th {{
  background: rgba(0,212,255,0.05);
}}

@media (max-width: 600px) {{
  .grid {{ grid-template-columns: 1fr; }}
  header h1 {{ font-size: 1.8rem; }}
  .tier-header {{ flex-wrap: wrap; }}
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
      stroke-dasharray="565.5" stroke-dashoffset="{565.5 * (1 - score['total']/10)}"
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

<!-- AI 分析摘要 -->
<div class="card">
  <h2>🧠 AI 分析摘要</h2>
  <div class="ai-summary">
    {ai_summary}
  </div>
  
  <h3 style="color: var(--accent); font-size: 0.9rem; margin: 1rem 0 0.5rem;">项目群健康度</h3>
  <div class="health-grid">
    {health_cards}
  </div>
  
  <h3 style="color: var(--accent); font-size: 0.9rem; margin: 1rem 0 0.5rem;">趋势判断</h3>
  {trends_html if trends_html else '<div class="trend-item">暂无趋势数据</div>'}
  
  <h3 style="color: var(--accent); font-size: 0.9rem; margin: 1rem 0 0.5rem;">改进建议</h3>
  {recs_html if recs_html else '<div class="rec-item">暂无建议</div>'}
</div>

<!-- 期望 vs 现实 差距矩阵 -->
<div class="card gap-matrix">
  <h2>📋 期望 vs 现实 差距矩阵</h2>
  <p style="color: var(--text-dim); font-size: 0.85rem; margin-bottom: 1rem;">
    对比 P*.json 期望状态与扫描现实，识别偏差并生成改进建议。
  </p>
  <table>
    <thead>
      <tr>
        <th>项目群</th>
        <th>期望状态（记忆中）</th>
        <th>扫描现实</th>
        <th>差距</th>
        <th>改进建议</th>
      </tr>
    </thead>
    <tbody>
      {gap_rows}
    </tbody>
  </table>
</div>

<!-- 告警详情 -->
<div class="card" style="margin-bottom: 2rem;">
  <h2>告警详情</h2>
  {alerts_html}
</div>

<!-- 四层项目树形展示 -->
<div class="card" style="margin-bottom: 2rem;">
  <h2>🏗️ 四层项目结构</h2>
  <p style="color: var(--text-dim); font-size: 0.85rem; margin-bottom: 1rem;">
    P0=赚钱 · P1=自进化 · P2=社交 · P3=用户任务
  </p>
  {tier_tree_html}
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
    <div class="metric"><span>Git 分支</span><span class="metric-value">{git.get("branch", "-")}</span></div>
    <div class="metric"><span>未提交</span><span class="metric-value">{"有" if git.get("has_uncommitted") else "无"}</span></div>
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
    本报告由 P1.0 baseline-check Skill（v3 AI+Gap 架构）自动生成。以下展示该 Skill 的完整文档和所有模块源码，供审计和改进。
  </p>
{''.join(skill_sections)}
</div>

<footer>
  <p>小K · P1.0 自成长系统 · 全面状态检查</p>
  <p style="margin-top: 0.5rem;">报告由 P1.0 baseline-check Skill 自动生成 · 部署于 littlek.trust4.net</p>
</footer>

</div>

<script>
// 评分维度柱状图
const scoreData = {score_data_json};
const scoreContainer = document.getElementById('score-bars');
const labels = {{'projects':'项目','environment':'环境','memory':'记忆','capabilities':'能力','trend':'趋势'}};
for (const [dim, val] of Object.entries(scoreData)) {{
  const bar = document.createElement('div');
  bar.className = 'chart-bar';
  const label = labels[dim] || dim;
  const color = val >= 8 ? 'var(--good)' : (val >= 5 ? 'var(--accent)' : 'var(--warn)');
  bar.innerHTML = `
    <div class="chart-label">${{label}}</div>
    <div class="chart-fill" style="width: ${{val * 10}}%; background: ${{color}}" data-value="${{val}}"></div>
  `;
  scoreContainer.appendChild(bar);
}}

// 注入原始 JSON
const rawData = {json.dumps(report, indent=2, ensure_ascii=False)};
document.getElementById('raw-json').textContent = JSON.stringify(rawData, null, 2);
</script>

</body>
</html>"""
    return html


def main():
    # 读取输入
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            report = json.load(f)
    else:
        stdin_data = sys.stdin.read()
        if not stdin_data.strip():
            latest_path = f"{REPORTS_DIR}/latest.json"
            if os.path.exists(latest_path):
                with open(latest_path, "r") as f:
                    report = json.load(f)
                print(f"读取已存在报告: {latest_path}")
            else:
                print("错误: 未提供输入且找不到 latest.json")
                sys.exit(1)
        else:
            report = json.loads(stdin_data)
    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(f"{REPORTS_DIR}/history", exist_ok=True)
    
    # 1. 写入 JSON
    json_path = f"{REPORTS_DIR}/latest.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"→ JSON: {json_path}")
    
    # 2. 写入 Markdown
    md_path = f"{REPORTS_DIR}/latest.md"
    md_content = generate_markdown(report)
    with open(md_path, "w") as f:
        f.write(md_content)
    print(f"→ Markdown: {md_path}")
    
    # 3. 写入 HTML（主页 + 备份）
    html_path = f"{WORKSPACE}/p1-dashboard.html"
    html_content = generate_html(report)
    with open(html_path, "w") as f:
        f.write(html_content)
    print(f"→ HTML: {html_path}")
    
    html_backup = f"{REPORTS_DIR}/latest.html"
    with open(html_backup, "w") as f:
        f.write(html_content)
    print(f"→ HTML backup: {html_backup}")
    
    # 历史归档（不覆盖已有）
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    for suffix, content in [(".json", json.dumps(report, indent=2, ensure_ascii=False)),
                            (".md", md_content)]:
        hist_path = f"{REPORTS_DIR}/history/{timestamp}{suffix}"
        with open(hist_path, "w") as f:
            f.write(content)
    print(f"→ 历史归档: {REPORTS_DIR}/history/{timestamp}.*")
    
    print("\n✅ 报告生成完成")


if __name__ == "__main__":
    main()
