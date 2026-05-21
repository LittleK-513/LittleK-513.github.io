# report v1 — P1.0 报告生成 Skill

> 目的：将 baseline-check 结果转化为可执行的行动清单
> 调用时机：baseline-check 发现告警时、P1.0 周期结束时、用户询问时
> 输出：Markdown 报告，包含：现状摘要 + 告警清单 + 建议行动 + 优先级排序

---

## 输入

读取 `state.json` 的 `last_baseline` JSON，或接收 baseline-check 的实时输出。

---

## 输出结构

### 1. 现状摘要（1-3 句话）

示例：
> **状态：良好（7.8/10）**。8/12 项目活跃，环境稳定，GitHub API 暂不可用（PAT 可能过期）。

### 2. 告警清单（如有）

按 severity 分级：

| 级别 | 图标 | 含义 | 响应时间 |
|------|------|------|----------|
| 🔴 critical | 红色 | 阻塞 P0 或核心能力 | 立即 |
| 🟡 warning | 黄色 | 可能恶化或长期停滞 | 本周期内 |
| 🟢 info | 绿色 | 值得注意但非紧急 | 下次 baseline |

格式：
```
🔴 [critical] GitHub API 失效 — 影响 P0 bounty 推进
   建议：检查 PAT 有效期，或让浩然更新 token

🟡 [warning] P2 已 stale 14 天 — Agent 社交网络无互动
   建议：spawn 轻量子 agent 做一次探测
```

### 3. 建议行动（按优先级排序）

每条行动包含：
- 动作（spawn / exec / 等待 / 通知用户）
- 目标项目
- 预估时间
- 验收标准

示例：
```
1. [立即] 修复 GitHub API → exec `gh auth status`，如失败通知浩然
2. [本周期] 推进 P2 → spawn 子 agent，做一次 Moltbook 探测
3. [观察] P1 状态漂移 → 下次 baseline 对比 hermes-lite vs p1-0 目录
```

### 4. 趋势对比（如有历史）

与上次 baseline 对比：
- 总分变化：7.8 → 8.2（+0.4）
- 新增项目：xxx
- 修复项：context pressure 已解决
- 恶化项：GitHub API 失效

### 5. 周期性报告（周/月）

当触发 weekly/monthly 报告时，额外包含：
- 本周完成的项目推进
- 本周新发现的机制缺陷
- 下周重点（自动从 state.json 的 `next_steps` 提取）

---

## 用户交互模式

### 模式 A：主动推送（自动）

条件：baseline 发现 🔴 critical 或状态分 < 6.0

输出：精简到 3 条以内，直接说明需要什么（用户动作 or 子 agent 动作）

示例：
> 🔴 GitHub API 挂了，P0 没法推进。需要浩然更新 PAT，或者我先尝试重新认证？

### 模式 B：用户询问（被动）

条件：用户问"P0 咋样了"或"今天状态"

输出：完整摘要 + 告警 + 下一步

### 模式 C：周期结束（P1.0 act 后）

条件：P1.0 一个 act 周期完成

输出：做了什么 + 结果 + 还缺什么 + 下次计划

---

## 写入位置

| 报告类型 | 文件路径 | 保留策略 |
|----------|----------|----------|
| 每次 baseline | `state.json[last_baseline]` | 覆盖 |
| 周期报告 | `projects/p1-self-evolution/reports/YYYY-MM-DD-HHMM.md` | 保留 30 天 |
| 周报告 | `projects/p1-self-evolution/reports/weekly/YYYY-WXX.md` | 保留 90 天 |
| 月报告 | `projects/p1-self-evolution/reports/monthly/YYYY-MM.md` | 永久 |

---

## 与其他 Skill 的关系

```
baseline-check ──→ 原始数据（JSON）
       ↓
  report-v1 ──→ 人类可读报告（Markdown）
       ↓
  plan-v1 ──→ 可执行计划（Action Items）
       ↓
execute-v1 ──→ 实际执行（spawn/exec）
       ↓
self-check-v1 ──→ 验证执行结果
```

---

## 调用方式

```bash
# 作为 P1.0 周期的一部分，由 baseline-check 自动触发
python3 /root/.openclaw/workspace/skills/p1-0/report.py --input state.json --output reports/

# 用户询问时手动调用
python3 /root/.openclaw/workspace/skills/p1-0/report.py --mode user-query --project P0
```
