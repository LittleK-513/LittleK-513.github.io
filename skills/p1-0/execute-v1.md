# execute v1 — P1.0 计划执行 Skill

> **目的**：消费 plan-v1 生成的 `current_plan`，逐项执行 action，记录执行结果
> **调用时机**：plan-v1 完成后、P1.0 周期执行阶段、用户要求"执行计划"时
> **输出**：执行日志写入 `state.json` 的 `execution_log`，各项目 state.json 就地更新

---

## 输入

读取 `state.json` 的 `current_plan`，关注以下字段：

```json
{
  "plan_version": "plan-v1",
  "generated_at": "2026-05-21T22:30:00+08:00",
  "cycle_id": "cycle-20260521-2230",
  "baseline_score": 6.5,
  "total_items": 3,
  "execution_mode": "sequential",
  "items": [
    {
      "plan_id": "plan-20260521-001",
      "source_alert": { "level": "warning", "category": "project", "item": "bounty stale 51h" },
      "priority": 1,
      "action": "spawn",
      "target_project": "bounty",
      "description": "推进 bounty 项目，检查 blocker 并执行 next action",
      "estimated_time": "30m",
      "deadline": "2026-05-21T23:15:00+08:00",
      "success_criteria": [ "项目 state.json 被更新", "last_action 字段有新增记录" ],
      "fallback": { "if_failed": "notify", "message": "bounty 推进失败，需要人工介入" }
    }
  ],
  "watchlist": [ ... ],
  "user_notifications": [ ... ]
}
```

---

## Action 类型映射表

| action 代码 | 对应 plan-v1 名称 | 执行方式 | 适用场景 | 并发限制 |
|------------|------------------|---------|---------|---------|
| `spawn` | spawn | 创建子 agent（lightContext=true），赋予独立 session | 项目推进、复杂任务、需要上下文隔离 | 同时不超过 2 个 |
| `exec` | exec | 当前 session 内直接执行 shell 命令或脚本 | 环境清理、轻量探测、状态检查 | 同时不超过 3 个 |
| `wait` | 等待 | 不执行，记录到 `watchlist`，设置下次检查时间 | 条件不成熟、需观察、负载过高 | 无限制 |
| `notify` | 通知用户 | 通过 message 工具向用户发送通知，等待人工介入 | 需人工决策、PAT 过期、OAuth 失效 | 立即发出 |

**类型归一化**：plan-v1 输出中的 `等待` 和 `通知用户` 在执行阶段统一归一化为 `wait` 和 `notify`，execute-v1 内部不做区分。

---

## 执行流程图

```
┌─────────────────────────────────────┐
│  读取 state.json[current_plan]        │
│  提取 items[], watchlist[],           │
│  user_notifications[]                 │
└──────────────┬────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Step 0: 前置处理                    │
│  • 立即发送 user_notifications         │
│  • 将 watchlist 合并到 state.json      │
│  • 按 priority 排序 items              │
└──────────────┬────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Step 1: 判断 execution_mode           │
│  sequential → 逐个执行               │
│  parallel   → 分组并发执行           │
│  observe    → 仅处理 watchlist       │
└──────────────┬────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Step 2: 遍历 items[]                │
│  对每个 item：                       │
│  ├─ 检查 deadline 是否已过期         │
│  ├─ 根据 action 类型分发执行         │
│  ├─ 记录执行结果到 execution_log     │
│  └─ 检查 success_criteria            │
│     ├─ 满足 → 标记成功               │
│     └─ 不满足 → 触发 fallback        │
└──────────────┬────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Step 3: 收尾与状态写入              │
│  • 汇总 execution_summary            │
│  • 写入 state.json[execution_log]    │
│  • 如有失败项，触发 report-v1 简报    │
└──────────────────────────────────────┘
```

---

## 四步执行法

### Step 0: 前置处理

1. **发送通知**：遍历 `user_notifications[]`，对每条调用 `message` 工具发送给用户
2. **合并 watchlist**：将 `watchlist` 写入 `state.json` 的 `pending_watchlist`
3. **排序 items**：按 `priority` 升序排列（1 最先执行）
4. **deadline 检查**：标记已过期（`deadline < now`）的 item，记录 `deadline_expired=true`

### Step 1: 执行模式判定

根据 `current_plan.execution_mode` 选择策略：

| execution_mode | 条件（plan-v1 设定） | 行为 |
|----------------|---------------------|------|
| `sequential` | 有 critical 告警 或 总分 < 6.0 | 按 priority 顺序逐个执行，完成一项才启动下一项 |
| `parallel` | 无 critical，总分 >= 6.0，warning 项 >= 3 | 同 category 的 warning 项可并发；spawn 最多 2 个并行，exec 最多 3 个并行 |
| `observe` | 无 critical，无 warning，总分 >= 8.0 | 不执行 items，仅处理 watchlist，等待下次 baseline |

### Step 2: 逐项执行

#### 2.1 `spawn` — 子 Agent 执行

**流程**：
1. 提取 `target_project` 和 `description`
2. 构造子 agent 任务描述（包含项目路径、目标、success_criteria）
3. 以 `lightContext=true` spawn 子 agent
4. 子 agent 完成后，收集其最终响应
5. 验证 success_criteria（检查目标项目 state.json 是否更新、文件是否变动等）

**子 agent 任务模板**：
```
你是 P1.0 执行子 agent，负责推进项目 {target_project}。

任务：{description}

验收标准：
{success_criteria}

要求：
- 读取项目目录下的 state.json 了解当前状态
- 识别 blocker 并尝试解决
- 执行下一步行动
- 完成后返回：做了什么、结果如何、是否满足验收标准
```

**成功判定**：
- 子 agent 正常返回且未报错
- 至少满足一条 success_criteria（通过文件检查验证）

**失败降级**（fallback）：
- 子 agent 超时（默认 30 分钟）→ 触发 fallback
- 子 agent 报错或崩溃 → 触发 fallback
- success_criteria 全部不满足 → 触发 fallback

#### 2.2 `exec` — 直接执行

**流程**：
1. 根据 `target_project` 或 `description` 解析待执行的命令/脚本
2. 在当前 session 内通过 `exec` 工具执行
3. 收集 stdout / stderr / exit code
4. 根据 exit code 和输出内容判定成败

**命令解析规则**：

| category | 典型命令示例 |
|----------|-------------|
| environment | `python3 scripts/disk-cleanup.py` / `openclaw gateway restart` |
| project | `python3 projects/{name}/project-status.py` / `cd {path} && git status` |
| capability | `gh auth status` / `curl -s https://api.github.com/user` |
| memory | `git checkout HEAD -- MEMORY.md` / `python3 scripts/diary-check.py` |

**成功判定**：
- exit code == 0 且 输出不含 "error" / "failed" / "unauthorized"（大小写不敏感）
- 或命令特定的成功标志（如 `gh auth status` 返回 `✓`）

**失败降级**：
- exit code != 0 → 触发 fallback
- 输出含错误关键字 → 触发 fallback
- 命令超时（默认 5 分钟）→ 触发 fallback

#### 2.3 `wait` — 等待观察

**流程**：
1. 不执行任何操作
2. 将 item 原样写入 `state.json[pending_watchlist]`
3. 设置 `check_at` 为当前时间 + estimated_time（默认 1 小时后复查）
4. 记录执行状态为 `deferred`

**行为**：wait 项不产生成功/失败判定，仅标记为已排期观察。

#### 2.4 `notify` — 通知用户

**流程**：
1. 构造通知消息（包含 plan_id、source_alert、所需用户动作）
2. 通过 `message` 工具发送给用户
3. 记录发送状态（成功/失败）到 execution_log
4. 标记 item 状态为 `notified`，等待用户响应

**消息模板**：
```
🔔 [P1.0 执行通知]
计划项：{plan_id}
来源：{source_alert.category} — {source_alert.item}
说明：{description}

需要你协助：
{fallback.message 或 自定义请求}

如有更新请回复，我将继续执行。
```

### Step 3: 收尾与状态写入

**汇总执行结果**：

```json
{
  "execution_version": "execute-v1",
  "cycle_id": "cycle-20260521-2230",
  "executed_at": "2026-05-21T22:35:00+08:00",
  "completed_at": "2026-05-21T23:10:00+08:00",
  "summary": {
    "total_items": 3,
    "succeeded": 2,
    "failed": 0,
    "deferred": 1,
    "notified": 0
  },
  "log": [
    {
      "plan_id": "plan-20260521-001",
      "action": "spawn",
      "target_project": "bounty",
      "status": "success",
      "started_at": "2026-05-21T22:35:00+08:00",
      "completed_at": "2026-05-21T23:05:00+08:00",
      "elapsed_minutes": 30,
      "result": "子 agent 正常返回，bounty/state.json 已更新，last_action 新增记录",
      "success_criteria_met": ["state.json 被更新", "last_action 字段有新增记录"],
      "fallback_triggered": false
    },
    {
      "plan_id": "plan-20260521-002",
      "action": "exec",
      "target_project": "p0-github-money",
      "status": "success",
      "started_at": "2026-05-21T23:05:00+08:00",
      "completed_at": "2026-05-21T23:08:00+08:00",
      "elapsed_minutes": 3,
      "result": "exit_code=0, gh auth 正常，bounty 列表已更新",
      "success_criteria_met": ["目录有文件修改", "候选列表被更新"],
      "fallback_triggered": false
    },
    {
      "plan_id": "plan-20260521-003",
      "action": "wait",
      "target_project": null,
      "status": "deferred",
      "started_at": "2026-05-21T23:08:00+08:00",
      "completed_at": "2026-05-21T23:08:00+08:00",
      "elapsed_minutes": 0,
      "result": "已加入 watchlist，预计 2026-05-22T10:00:00+08:00 复查",
      "success_criteria_met": [],
      "fallback_triggered": false
    }
  ]
}
```

**写入位置**：
- 主执行日志：`state.json` → `execution_log`
- 历史归档：`projects/p1-self-evolution/executions/YYYY-MM-DD-HHMM.json`
- 清空 `current_plan`（或标记为 `consumed`），避免重复执行

---

## 与 plan-v1 的接口定义

| 接口 | 方向 | 数据 | 格式 |
|------|------|------|------|
| 输入 | plan-v1 → execute-v1 | `state.json[current_plan]` | JSON，含 items / watchlist / user_notifications |
| 输出 | execute-v1 → state.json | `state.json[execution_log]` | JSON，含 summary + log[] |
| 副作用 | execute-v1 → 各项目 | 项目目录 `state.json` | 原地更新 last_action / blocker 等字段 |
| 触发 | execute-v1 → self-check-v1 | 执行完成后自动触发 | 传递 execution_log 和更新后的项目 state |

**关键约定**：
1. execute-v1 不修改 `current_plan` 的结构，只读取
2. 执行完成后，`current_plan` 标记为 `consumed=true`，或移至 `plan_history`
3. 子 agent 对项目 state.json 的修改由子 agent 自行完成，execute-v1 只验证结果
4. watchlist 和 user_notifications 即使 plan 被消费后也保留，供下次 baseline 参考

---

## 错误处理策略

### 层级 1: Action 级别错误

| 错误类型 | 处理策略 | 日志记录 |
|---------|---------|---------|
| spawn 超时 | 终止子 agent，标记 `timeout`，触发 fallback | `status: failed, reason: timeout` |
| spawn 崩溃 | 捕获异常，标记 `crashed`，触发 fallback | `status: failed, reason: subagent_error` |
| exec 非零退出 | 记录 exit_code 和 stderr，触发 fallback | `status: failed, reason: exit_code=N` |
| exec 命令未找到 | 标记 `not_found`，触发 fallback | `status: failed, reason: command_not_found` |
| notify 发送失败 | 重试 1 次，仍失败则标记 `notify_failed` | `status: failed, reason: notify_failed` |

### 层级 2: Fallback 执行

当 action 失败时，按 `fallback.if_failed` 执行：

| fallback 类型 | 行为 |
|--------------|------|
| `notify` | 向用户发送 fallback.message，标记 item 为 `notified` |
| `exec` | 执行 fallback 命令（如降级脚本），标记 `fallback_executed` |
| `wait` | 将 item 移回 watchlist，标记 `deferred` |
| `skip` | 放弃该项，标记 `skipped`，记录原因 |

### 层级 3: 全局降级

当连续失败达到一定阈值时：

| 条件 | 全局行为 |
|------|---------|
| 同一 cycle 内 spawn 失败 >= 2 次 | 暂停后续 spawn，剩余 spawn 项全部降级为 `notify` |
| 同一 cycle 内 exec 失败 >= 3 次 | 暂停后续 exec，切换为 `sequential` 模式逐一排查 |
| 所有 items 均失败 | 触发紧急报告（report-v1 精简模式），直接通知用户 |
| 执行时间超过 plan deadline 总和 × 2 | 强制中断，记录 `execution_aborted`，通知用户 |

### 层级 4: 状态恢复

- 执行开始前备份 `state.json` 到 `state.json.bak`
- 任何异常中断后，可从备份恢复
- 执行日志采用追加写入，已完成的 item 记录不会丢失

---

## 与已有 Skill 的关系

```
baseline-check ──→ 发现问题（JSON 数据）
       ↓
  report-v1 ──→ 人类可读报告（Markdown）
       ↓
  plan-v1 ──→ 可执行计划（Action Items）
       ↓
execute-v1 ──→ 实际执行（spawn / exec / wait / notify）← 本文件
       ↓
self-check-v1 ──→ 验证执行结果（待写）
```

**接口约定**：

| 接口 | 输入 | 输出 |
|------|------|------|
| plan-v1 → execute-v1 | `state.json[current_plan]` | — |
| execute-v1 → 项目目录 | 子 agent / exec 命令 | 项目 state.json 更新 |
| execute-v1 → self-check-v1 | `state.json[execution_log]` + 更新后的项目 state | 验证报告 |
| execute-v1 → report-v1 | 执行摘要（当失败率 > 0 时） | 简报消息 |

---

## 并发控制

### spawn 并发

```
max_parallel_spawn = 2
spawn_queue = []

for item in spawn_items:
    if active_spawns < max_parallel_spawn:
        立即 spawn
        active_spawns += 1
    else:
        加入 spawn_queue，按 priority 排队

当任一 spawn 完成：
    active_spawns -= 1
    从 spawn_queue 取出下一个执行
```

### exec 并发

```
max_parallel_exec = 3
exec_batch = []

for item in exec_items:
    exec_batch.append(item)
    if len(exec_batch) >= max_parallel_exec:
        并行执行 batch，等待全部完成
        exec_batch = []

处理剩余 exec_batch（如果有）
```

**串行约束**：
- `sequential` 模式下，所有 action 严格串行
- 同一 `target_project` 的 `spawn` 项，无论模式均间隔 >= 1 小时（通过检查该项目的 last_action 时间戳）

---

## 示例：从计划到执行

### 输入（current_plan）

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
        "if_failed": "notify",
        "message": "bounty 项目推进失败，可能缺少上下文或权限"
      }
    },
    {
      "plan_id": "plan-20260521-002",
      "source_alert": { "level": "warning", "category": "environment", "item": "disk > 90%" },
      "priority": 2,
      "action": "exec",
      "target_project": null,
      "description": "清理磁盘：删除旧日志和缓存文件",
      "estimated_time": "5m",
      "deadline": "2026-05-21T23:30:00+08:00",
      "success_criteria": [
        "磁盘使用率降至 85% 以下"
      ],
      "fallback": {
        "if_failed": "notify",
        "message": "磁盘清理失败，请检查权限或手动清理"
      }
    }
  ],
  "watchlist": [],
  "user_notifications": [
    { "message": "GitHub PAT 将于 3 天后过期，建议提前更新" }
  ]
}
```

### 执行过程

1. **Step 0**：发送 user_notification（GitHub PAT 提醒）
2. **Step 1**：execution_mode = sequential → 逐项串行
3. **Item 1**（spawn bounty）：
   - 22:35 spawn 子 agent，任务：推进 bounty
   - 23:05 子 agent 返回，检查 bounty/state.json → last_action 已更新 ✅
   - 标记 `success`
4. **Item 2**（exec disk cleanup）：
   - 23:06 执行 `python3 scripts/disk-cleanup.py`
   - 23:08 完成，exit_code=0，磁盘使用率 83% ✅
   - 标记 `success`
5. **Step 3**：写入 execution_log，标记 current_plan 为 consumed

### 输出（execution_log）

```json
{
  "execution_version": "execute-v1",
  "cycle_id": "cycle-20260521-2230",
  "executed_at": "2026-05-21T22:35:00+08:00",
  "completed_at": "2026-05-21T23:08:00+08:00",
  "summary": { "total_items": 2, "succeeded": 2, "failed": 0, "deferred": 0, "notified": 0 },
  "log": [
    {
      "plan_id": "plan-20260521-001",
      "action": "spawn",
      "target_project": "bounty",
      "status": "success",
      "started_at": "2026-05-21T22:35:00+08:00",
      "completed_at": "2026-05-21T23:05:00+08:00",
      "elapsed_minutes": 30,
      "result": "子 agent 推进成功：检查了 bounty 状态，识别到 blocker 为'缺少测试环境'，已记录",
      "success_criteria_met": ["state.json 被更新", "last_action 字段被更新"],
      "fallback_triggered": false
    },
    {
      "plan_id": "plan-20260521-002",
      "action": "exec",
      "target_project": null,
      "status": "success",
      "started_at": "2026-05-21T23:06:00+08:00",
      "completed_at": "2026-05-21T23:08:00+08:00",
      "elapsed_minutes": 2,
      "result": "exit_code=0, 清理了 2.1GB 旧日志，磁盘使用率从 91% 降至 83%",
      "success_criteria_met": ["磁盘使用率降至 85% 以下"],
      "fallback_triggered": false
    }
  ]
}
```

---

## 调用方式

```bash
# 作为 P1.0 周期的一部分，由 plan-v1 自动触发
python3 /root/.openclaw/workspace/skills/p1-0/execute.py --input state.json

# 用户要求执行计划时手动调用
python3 /root/.openclaw/workspace/skills/p1-0/execute.py --mode manual --plan-id plan-20260521-001

# 输出
→ state.json[execution_log] 更新
→ current_plan 标记为 consumed
→ 如有失败项，触发 fallback（notify / exec / wait）
→ 完成后自动触发 self-check-v1（如有）
```

---

## 设计原则

1. **执行即消费**：current_plan 是一次性消费品，执行后必须标记 consumed，防止重复执行
2. **可观测**：每个 action 的开始、结束、结果、耗时全部记录，支持事后审计
3. **可降级**：任何失败都有 fallback 路径，不会无限阻塞或静默失败
4. **资源受控**：spawn 和 exec 的并发上限硬限制，避免资源耗尽
5. **幂等安全**：同一 plan_id 执行多次不会导致副作用叠加（通过 plan_id 去重检查）
6. **超时保护**：spawn 默认 30 分钟、exec 默认 5 分钟，防止僵尸任务
