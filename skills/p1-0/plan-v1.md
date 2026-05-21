# plan v1 — P1.0 计划生成 Skill

> 目的：将 baseline-check 的告警转化为可执行的行动计划
> 调用时机：baseline-check 完成后、report-v1 触发后、用户要求"制定计划"时
> 输出：结构化计划（JSON/YAML），写入 `state.json` 的 `current_plan`

---

## 输入

读取 `state.json` 的 `last_baseline`，关注以下字段：

```json
{
  "score": 6.5,
  "score_breakdown": { ... },
  "projects": [ { "name", "status", "tier", "age_hours", "blocker", "last_action" } ],
  "alerts": [ { "level", "category", "item", "suggestion" } ],
  "alert_count": { "critical", "warning", "info" },
  "capabilities": { "github_api", "web_search", "feishu", ... },
  "environment": { "disk", "memory", "load" }
}
```

---

## 四步计划生成法

### Step 1: 告警排序与分级

读取 `alerts` 数组，按以下规则排序：

1. **severity 优先级**：`critical` > `warning` > `info`
2. **同 severity 内**：按 `category` 分组（environment > project > capability > memory）
3. **同 category 内**：按 `age_hours` 降序（越老的越优先）

分级判定：

| severity | 响应策略 | 计划时间窗口 |
|----------|----------|-------------|
| 🔴 critical | 立即执行，阻塞其他行动 | 0-30 分钟 |
| 🟡 warning | 本周期内执行 | 30 分钟 - 4 小时 |
| 🟢 info | 下次 baseline 时复查 | 本次不生成计划 |

### Step 2: 告警 → 行动映射

对每个告警，根据 `category` 和 `item` 匹配预设映射规则：

| category | 典型 item | 默认 action | 说明 |
|----------|----------|------------|------|
| environment | disk > 90% | exec | 执行清理脚本 |
| environment | memory > 90% | exec | 重启 gateway 或清理 sessions |
| environment | load > 5.0 | 等待 | 观察，30 分钟后复测 |
| project | stale Nh + tier=P0 | spawn | spawn 子 agent 推进项目 |
| project | stale Nh + tier=P1 | spawn | spawn 子 agent，但可排队 |
| project | stale Nh + tier=P2 | exec | 轻量探测，不 spawn |
| project | orphan | exec | 扫描并归类 |
| project | ghost | exec | 清理空目录 |
| capability | GitHub API 失效 | 通知用户 | 需要 PAT 更新，需人工 |
| capability | feishu 失效 | 通知用户 | 需 OAuth 重新授权 |
| capability | tunnel 失效 | exec | 尝试重启 cloudflared |
| memory | 关键文件缺失 | exec | 从 git history 恢复 |
| memory | 7 天无日记 | spawn | spawn 子 agent 写 introspection |

action 类型定义：

- `spawn`：创建子 agent，赋予独立 session，执行具体任务
- `exec`：在当前 session 内直接执行命令或脚本
- `等待`：不生成行动，记录到 `watchlist`，下次 baseline 复查
- `通知用户`：通过 message 工具向用户发送通知，等待人工介入

### Step 3: 生成计划项

每个计划项（Plan Item）结构：

```json
{
  "plan_id": "plan-20260521-001",
  "source_alert": { "level": "warning", "category": "project", "item": "bounty stale 51h" },
  "priority": 1,
  "action": "spawn",
  "target_project": "bounty",
  "description": "推进 bounty 项目，检查 blocker 并执行 next action",
  "estimated_time": "30m",
  "deadline": "2026-05-21T23:15:00+08:00",
  "success_criteria": [
    "项目 state.json 被更新",
    "last_action 字段有新增记录",
    "或 blocker 被明确记录并升级通知"
  ],
  "fallback": {
    "if_failed": "通知用户",
    "message": "bounty 推进失败，需要人工介入"
  }
}
```

字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| plan_id | 是 | 格式 `plan-{YYYYMMDD}-{NNN}`，全局递增 |
| source_alert | 是 | 关联的原始告警 |
| priority | 是 | 1 最高，按 severity+age 计算 |
| action | 是 | spawn / exec / 等待 / 通知用户 |
| target_project | 条件 | action=spawn/exec 时必须；环境类可为空 |
| description | 是 | 人类可读的任务描述 |
| estimated_time | 是 | 预估耗时，格式：`5m` / `30m` / `1h` / `4h` |
| deadline | 否 | 根据 estimated_time 和 severity 自动计算 |
| success_criteria | 是 | 字符串数组，验收标准，必须可验证 |
| fallback | 否 | 失败时的降级策略 |

### Step 4: 计划编排与输出

**编排规则**：

1. critical 项必须独占执行窗口，不可并行
2. warning 项中，同 project 的项合并为一个综合计划
3. 同一 project 的 spawn 计划间隔 >= 1 小时，避免资源冲突
4. exec 类计划可并行，但同一时间不超过 3 个
5. 通知用户 类计划立即发出，不进入执行队列

**输出格式**：

```json
{
  "plan_version": "plan-v1",
  "generated_at": "2026-05-21T22:30:00+08:00",
  "cycle_id": "cycle-20260521-2230",
  "baseline_score": 6.5,
  "total_items": 3,
  "execution_mode": "sequential",
  "items": [
    { ...plan item 1... },
    { ...plan item 2... },
    { ...plan item 3... }
  ],
  "watchlist": [
    { "item": "p2-agent-social API 失效", "check_at": "2026-05-22T10:00:00+08:00" }
  ],
  "user_notifications": [
    { "message": "GitHub PAT 可能过期，请检查" }
  ]
}
```

**写入位置**：

- 主计划：`state.json` → `current_plan`
- 历史归档：`projects/p1-self-evolution/plans/YYYY-MM-DD-HHMM.json`

---

## 示例：从告警到计划

### 输入（baseline alerts）

```json
[
  { "level": "warning", "category": "project", "item": "bounty stale 51h", "suggestion": "检查 bounty 的 blocker 或推进 next action" },
  { "level": "warning", "category": "project", "item": "p0-github-money stale 0h", "suggestion": "检查 p0-github-money 的 blocker 或推进 next action" },
  { "level": "warning", "category": "project", "item": "p1-self-evolution stale 2h", "suggestion": "检查 p1-self-evolution 的 blocker 或推进 next action" },
  { "level": "warning", "category": "project", "item": "p2-agent-social stale 1h", "suggestion": "检查 p2-agent-social 的 blocker 或推进 next action" }
]
```

### 输出（current_plan）

```json
{
  "plan_version": "plan-v1",
  "generated_at": "2026-05-21T22:30:00+08:00",
  "cycle_id": "cycle-20260521-2230",
  "baseline_score": 6.5,
  "total_items": 2,
  "execution_mode": "sequential",
  "items": [
    {
      "plan_id": "plan-20260521-001",
      "source_alert": { "level": "warning", "category": "project", "item": "bounty stale 51h" },
      "priority": 1,
      "action": "spawn",
      "target_project": "bounty",
      "description": "推进 bounty 项目：读取项目状态，识别 blocker，执行下一步行动",
      "estimated_time": "30m",
      "deadline": "2026-05-21T23:00:00+08:00",
      "success_criteria": [
        "bounty 目录有文件修改或新增",
        "state.json 的 last_action 字段被更新",
        "若发现 blocker，记录到 state.json 的 blocker 字段"
      ],
      "fallback": {
        "if_failed": "通知用户",
        "message": "bounty 项目推进失败，可能缺少上下文或权限"
      }
    },
    {
      "plan_id": "plan-20260521-002",
      "source_alert": { "level": "warning", "category": "project", "item": "p0-github-money stale 0h" },
      "priority": 2,
      "action": "spawn",
      "target_project": "p0-github-money",
      "description": "推进 P0 项目：检查 GitHub bounty 状态，执行挖掘或提交行动",
      "estimated_time": "45m",
      "deadline": "2026-05-21T23:30:00+08:00",
      "success_criteria": [
        "p0-github-money 目录有文件修改",
        "bounty 候选列表被更新或新增提交记录"
      ],
      "fallback": {
        "if_failed": "通知用户",
        "message": "P0 bounty 推进受阻，GitHub API 状态需检查"
      }
    }
  ],
  "watchlist": [
    { "item": "p1-self-evolution stale 2h（P1 自身）", "check_at": "2026-05-21T23:30:00+08:00" },
    { "item": "p2-agent-social stale 1h（API 探测失败中）", "check_at": "2026-05-22T10:00:00+08:00" }
  ],
  "user_notifications": []
}
```

---

## 与已有 Skill 的关系

```
baseline-check ──→ 原始数据（JSON）
       ↓
  report-v1 ──→ 人类可读报告（Markdown）
       ↓
  plan-v1 ──→ 可执行计划（Action Items）← 本文件
       ↓
execute-v1 ──→ 实际执行（spawn/exec）
       ↓
self-check-v1 ──→ 验证执行结果
```

**接口约定**：

| 接口 | 输入 | 输出 |
|------|------|------|
| baseline-check → plan-v1 | `state.json[last_baseline]` | `state.json[current_plan]` |
| plan-v1 → execute-v1 | `state.json[current_plan]` | 执行结果写入各项目 `state.json` |
| execute-v1 → self-check-v1 | 各项目修改后的 `state.json` | 验证报告 |
| self-check-v1 → baseline-check | 触发新一轮 baseline | 循环闭环 |

---

## 执行策略

### 策略 A：顺序执行（默认）

条件：有 critical 告警 或 总分 < 6.0

行为：按 priority 顺序逐个执行，完成一项才启动下一项

### 策略 B：并行执行

条件：无 critical，总分 >= 6.0，且 warning 项 >= 3

行为：同 category 的 warning 项可并行，但同一时间 spawn 不超过 2 个

### 策略 C：仅观察

条件：无 critical，无 warning，总分 >= 8.0

行为：不生成 items，仅更新 `watchlist`，等待下次 baseline

---

## 调用方式

```bash
# 作为 P1.0 周期的一部分，由 report-v1 自动触发
python3 /root/.openclaw/workspace/skills/p1-0/plan.py --input state.json

# 用户要求制定计划时手动调用
python3 /root/.openclaw/workspace/skills/p1-0/plan.py --mode manual --project bounty

# 输出
→ state.json[current_plan] 更新
→ 如有 user_notifications，触发 message 工具
→ 如有 spawn 计划，排队等待 execute-v1 消费
```

---

## 设计原则

1. **可验证**：每个 success_criteria 必须是客观、可检查的（文件修改？字段更新？）
2. **可降级**：每个 spawn/exec 计划必须有 fallback，避免无限阻塞
3. **可追踪**：plan_id 全局唯一，执行日志需记录 plan_id
4. **轻量**：plan 阶段只做"计划"，不做执行——执行交给 execute-v1
5. **透明**：生成的计划必须人类可读，用户可随时查看 current_plan
