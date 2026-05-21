# P1.0 heartbeat-check.py 机制修复日志

## 时间
2026-05-21 23:10

## 发现的问题
heartbeat-check.py 报告 P2 idle=19.7h（触发推进），但实际 projects/p2-agent-social/state.json 最后更新是 1.2h 前。

## 根因分析
1. **`break` 过早退出**：遍历 projects/ 目录时，`p2-moltbook` 排在 `p2-agent-social` 前面，遇到第一个 `p2-*` 匹配就 `break`，导致永远读不到 `p2-agent-social` 的状态
2. **时区比较静默失败**：`best_time` 初始化为 naive datetime（无时区），但项目 `last_updated` 带 `+08:00` 时区。`pt > best_time` 抛出 `can't compare offset-naive and offset-aware`，异常被吞掉，导致 `best_proj` 永远为空

## 修复内容
- 移除 `break`，改为遍历所有匹配目录
- 初始化 `best_time` 为 UTC 时区 aware datetime
- 比较前统一将 naive datetime 转为 UTC aware
- 选择 `last_updated` 最新的项目状态作为有效状态

## 修复后验证
```
P0: idle=1.3h ✅ (无需推进)
P1: idle=5.5h ✅ (无需推进)
P2: idle=1.3h ✅ (无需推进)
```

## 教训
- 异常静默吞掉 =  hardest bug
- naive vs aware datetime 比较必须显式处理时区
- `break` 在遍历逻辑中是常见陷阱

---
*修复者：主 agent（heartbeat 执行过程中自发现、自修复）*
