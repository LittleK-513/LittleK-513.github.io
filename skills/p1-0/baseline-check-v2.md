# baseline-check v3 — P1.0 全面状态检查 Skill（AI 分析 + 差距矩阵 + 四层结构）

> **Purpose**: 全面扫描系统状态，AI 分析洞察，期望 vs 现实对比，生成 JSON + Markdown + HTML 仪表板
> **Invocation**: 每次 P1.0 周期启动时、heartbeat 触发时、用户询问状态时
> **Architecture**: 文档(this file) + 7个检查模块 + 编排器(AI+Gap) + 报告生成器

---

## 技能组成

| 组件 | 文件 | 作用 |
|------|------|------|
| **Skill 文档** | `skills/p1-0/baseline-check-v2.md` | 本文档 — 定义检查逻辑、输出格式、调用方式 |
| **模块层** | `skills/p1-0/modules/check-*.py` | 7个独立检查模块，各输出标准 JSON |
| **编排器** | `skills/p1-0/orchestrator.py` | 并行运行模块 → AI 分析 → 差距矩阵 → 评分 → 告警 |
| **报告生成器** | `skills/p1-0/generate-report.py` | 从统一 JSON 生成 Markdown + HTML（四层树+AI+Gap） |
| **Skill 状态** | `skills/p1-0/state.json` | 记录上次检查结果和历史 |
| **输出目录** | `reports/p1-0/` | 每次运行生成 JSON + Markdown + HTML |
| **部署位置** | `p1-dashboard.html` | 主页仪表板，自动覆盖更新 |

---

## 模块架构

```
skills/p1-0/modules/
├── check-model.py         → 模型与运行时信息
├── check-harness.py       → Harness 机制（Gateway、cron、systemd、sessions）
├── check-memory.py        → 记忆系统（关键文件、日记活跃度）
├── check-projects.py      → 项目审计（四层结构：P0/P1/P2/P3）
├── check-environment.py   → 运行环境（磁盘、内存、负载、Git）
├── check-capabilities.py  → 能力验证（GitHub、飞书、Tunnel、邮件）
└── check-sessions.py      → 会话历史（最近 session 文件）
```

**每个模块接口标准**:
- 独立可运行: `python3 check-xxx.py`
- 输出格式: `{"module": "xxx", "data": {...}, "checks_passed": N, "checks_total": M}`
- 错误处理: 单个模块失败不影响其他模块
- 超时保护: 每个模块最多 30 秒

---

## 四层项目群结构

```
P0: GitHub 赚钱任务
  └── bounty           (旧项目目录)
  └── p0-github-money  (projects/ 下的新项目)

P1: 自进化任务
  └── p1-self-evolution
  └── hermes-lite      (P1 工具/能力)

P2: 社交网络探索
  └── p2-agent-social
  └── p2-moltbook

P3: 用户安排的其它任务
  └── （预留，目前无项目）
```

**check-projects.py 输出结构**:
```json
{
  "module": "projects",
  "data": {
    "groups": [
      {
        "tier": "P0",
        "name": "P0: GitHub 赚钱任务",
        "goal": "...",
        "projects": [...],
        "stats": {"total":2, "active":0, "stale":2, "orphan":0, "ghost":0},
        "group_score": 0,
        "group_status": "stale",
        "group_health": "🟠 全面停滞"
      }
    ]
  }
}
```

---

## AI 分析模块

**位置**: `orchestrator.py` 内嵌 `perform_ai_analysis()`

**分析维度**:
1. **健康度评估**: 每个项目群评分 (0-10) + 状态标签
2. **异常识别**: 磁盘 >85%、项目停滞 >72h、关键文件缺失、日记断更、API 失效
3. **趋势判断**: 与上次 baseline 对比评分变化、活跃项目占比、磁盘趋势
4. **改进建议**: 按优先级 (immediate/this_cycle) 排序的 action 列表

**输出结构**:
```json
{
  "ai_analysis": {
    "summary": "本周期扫描到 6 个项目...",
    "health_assessment": {"P0": {"score": 0, "status": "stale", "notes": [...]}, ...},
    "anomalies": [{"severity": "high", "category": "...", "finding": "...", "detail": "..."}],
    "trends": ["➡️ 系统健康度持平（6.2 分）", ...],
    "recommendations": [{"priority": "immediate", "target": "projects", "action": "..."}]
  }
}
```

**实现方式**: 规则驱动 + 启发式分析（不单独 spawn 子 agent，在 orchestrator 内一次完成）

---

## 期望 vs 现实 差距矩阵

**数据源**:
- `references/self-evolution/state/P0.json` — P0 期望状态
- `references/self-evolution/state/P1.json` — P1 期望状态
- `references/self-evolution/state/P2.json` — P2 期望状态
- `MEMORY.md` — 记忆中的期望线索

**对比维度**:
| 列 | 说明 |
|----|------|
| 项目群 | P0/P1/P2/P3 |
| 期望状态 | 从 P*.json 提取的 current_step / last_action / next_steps / blocker |
| 扫描现实 | 实际项目活跃/停滞数量 + 具体项目名称 |
| 差距 | ✅ 符合 / 🟡 偏差 / 🔴 严重偏差 / ⚪ 未启动 |
| 改进建议 | 自动生成的 action（检查 blocker / 推进 next action / 维持节奏） |

**输出结构**:
```json
{
  "gap_matrix": [
    {
      "tier": "P0",
      "tier_name": "P0: GitHub 赚钱任务",
      "expected": "当前阶段: scan_new_issue | 最近动作: ...",
      "reality": "0/2 活跃 | 停滞: bounty, p0-github-money",
      "gap": "🔴 严重偏差",
      "gap_reason": "全部项目停滞",
      "suggestion": "检查 blocker，激活 P0 任务"
    }
  ]
}
```

---

## 评分算法

| 维度 | 权重 | 计算方式 |
|------|------|---------|
| 项目健康度 | 30% | 项目群加权平均分（按项目数加权），active 比例 × 10 |
| 环境稳定度 | 20% | 环境检查通过项 / 总检查项 × 10（磁盘>85%扣2分，>95%扣3分） |
| 记忆完整度 | 20% | 关键文件存在 + 日记更新及时 = 10（<3篇扣2分） |
| 能力可用度 | 20% | 外部连接可用数 / 总连接数 × 10 |
| 历史趋势 | 10% | 与上次 baseline 对比（默认持平） |

**总分** = Σ(维度分 × 权重)，0-10 分
**评级** = A(≥8) / B(≥6) / C(≥4) / D(<4)

---

## 告警分级

| 级别 | 图标 | 响应策略 | 计划时间窗口 |
|------|------|---------|-------------|
| 🔴 critical | 红色 | 阻塞 P0 或核心能力 | 立即执行 |
| 🟡 warning | 黄色 | 可能恶化或长期停滞 | 本周期内 |
| 🟢 info | 绿色 | 值得注意但非紧急 | 下次 baseline |

**新增告警类型**: `project_group`（项目群级别，替代原来的单个项目告警）

---

## 输出格式

### 1. JSON 数据包 (`reports/p1-0/latest.json`)
完整结构化数据，包含 meta / score / modules / **ai_analysis** / **gap_matrix** / alerts

### 2. Markdown 报告 (`reports/p1-0/latest.md`)
人类可读摘要，包含：
- 评分表格
- **AI 分析摘要** + 健康度 + 趋势 + 建议
- **期望 vs 现实差距矩阵**
- 告警清单
- 四层项目结构（按 P0/P1/P2/P3 分组）
- 环境/Harness/记忆/能力

### 3. HTML 仪表板 (`p1-dashboard.html`)
暗色赛博朋克主题，包含：
- 评分圆环可视化
- 告警卡片
- **🧠 AI 分析摘要**（健康度卡片网格 + 趋势 + 建议）
- **📋 期望 vs 现实差距矩阵**（5 列表格）
- **🏗️ 四层项目结构**（树形卡片：tier badge + 项目列表）
- 环境/Harness/记忆/能力四宫格
- Skill 源码章节（可折叠）
- 原始 JSON 数据（可折叠）

---

## 调用方式

```bash
# 完整流程（编排器 + 报告生成）
python3 /root/.openclaw/workspace/skills/p1-0/orchestrator.py | \
  python3 /root/.openclaw/workspace/skills/p1-0/generate-report.py

# 或分步执行
python3 /root/.openclaw/workspace/skills/p1-0/orchestrator.py
python3 /root/.openclaw/workspace/skills/p1-0/generate-report.py

# 输出位置
# → reports/p1-0/latest.json
# → reports/p1-0/latest.md
# → p1-dashboard.html（主页）
# → skills/p1-0/state.json[last_baseline]
```

---

## 与其他 Skill 的关系

```
baseline-check-v3 ──→ 全面检查 + AI 分析 + 差距矩阵 + 可视化报告
       ↓
  plan-v1 ──→ 生成可执行计划
       ↓
execute-v1 ──→ 实际执行（spawn/exec）
       ↓
self-check-v1 ──→ 验证执行结果
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1 | 2026-05-21 | 单体脚本 p1-baseline.py |
| v2 | 2026-05-22 | 模块化：7 模块 + orchestrator + generate-report |
| **v3** | **2026-05-22** | **+ AI 分析 + 期望 vs 现实差距矩阵 + 四层项目结构** |

---

*Version: v3-ai-gap | Updated: 2026-05-22*
