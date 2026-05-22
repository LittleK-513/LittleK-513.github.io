# P1.0 系统状态报告

> 生成时间：2026-05-22T09:59:54.623948
> 版本：p1-baseline-v3-ai-gap
> 工作区：/root/.openclaw/workspace

---

## 综合评分：6.2/10（B 级）

| 维度 | 得分 | 权重 | 加权 |
|------|------|------|------|
| projects | 2.3 | 30% | 0.69 |
| environment | 10 | 20% | 2.0 |
| memory | 10 | 20% | 2.0 |
| capabilities | 5.0 | 20% | 1.0 |
| trend | 5 | 10% | 0.5 |

---

## AI 分析摘要

本周期扫描到 6 个项目分布在 3 个项目群中。系统健康评分 6.2/10，未发现显著异常，系统运行平稳。项目群状况: P0 群全面停滞；P1 群部分停滞（1/2）；P2 群部分停滞（1/2）。

### 健康度评估
- **P0**: 评分 0/10，状态 stale
  - ⚠️ P0 有 2/2 个项目停滞
  -    最老停滞: bounty (62h)
- **P1**: 评分 3.5/10，状态 mixed
  - ⚠️ P1 有 1/2 个项目停滞
  -    最老停滞: p1-self-evolution (13h)
- **P2**: 评分 3.5/10，状态 mixed
  - ⚠️ P2 有 1/2 个项目停滞
  -    最老停滞: p2-agent-social (12h)

### 趋势判断
- ➡️ 系统健康度持平（6.2 分）
- ⚠️ 活跃项目仅占 33%，多数项目停滞
- 🟡 磁盘使用率偏高，建议纳入下周清理计划

### 改进建议
- 🟡 **projects**: 激活停滞项目: bounty, p0-github-money, p1-self-evolution

---

## 期望 vs 现实 差距矩阵

| 项目群 | 期望状态 | 扫描现实 | 差距 | 改进建议 |
|--------|----------|----------|------|----------|
| P0 | 当前阶段: scan_new_issue | 最近动作: [2026-05-19 03:45] Pushed 4-Age… | 0/2 活跃 | 停滞: bounty, p0-github-money… | 🔴 严重偏差 | 检查 blocker，激活 P0 任务… |
| P1 | 当前阶段: report | 最近动作: P1.0 Skills 固化推进：baseline-check-v2.md +… | 1/2 活跃 | 停滞: p1-self-evolution | 活跃: her… | 🟡 偏差 | 推进 next action，激活停滞项目… |
| P2 | 当前阶段: agent_community_interact | 最近动作: ✅ Agent Community 轻量互… | 1/2 活跃 | 停滞: p2-agent-social | 活跃: p2-mo… | 🟡 偏差 | 推进 next action，激活停滞项目… |
| P3 | 未记录期望… | 无项目… | ⚪ 未启动 | 启动 用户指派任务… |

---

## 告警清单

| 级别 | 类别 | 问题 | 建议 |
|------|------|------|------|
| 🔴 critical | project_group | P0: GitHub 赚钱任务 全面停滞 (2/2 项目 stale) | 检查 P0 项目群的 blocker，优先激活 |
| 🟡 warning | project_group | P1: 自进化任务 部分停滞: p1-self-evolution | 推进 P1 停滞项目的 next action |
| 🟡 warning | project_group | P2: 社交网络探索 部分停滞: p2-agent-social | 推进 P2 停滞项目的 next action |

---

## 运行环境

```
主机：VM-13-249-ubuntu
运行时间：09:59:52 up 14 days, 17:00,  0 user,  load average: 0.15, 0.29, 0.25
磁盘：/dev/vda2        40G   32G  6.5G  83% /
内存：Mem:           7.5Gi       2.8Gi       889Mi       6.1Mi       4.2Gi       4.7Gi
Node.js：v24.15.0
Python：Python 3.12.3
OpenClaw：OpenClaw 2026.4.14 (323493f)
```

---

## Harness 机制

| 检查项 | 状态 |
|--------|------|
| Cron Jobs | 9 条 |
| Gateway | Service: systemd (en... |
| Sessions | 242 个文件，共 141.0MB |
| Git 分支 | main |
| Git 未提交 | 有 |
| 上次提交 | 90e2f68e @ 2026-05-22 05:58:27 +0800 |

### Cron Jobs

```
*/5 * * * * flock -xn /tmp/stargate.lock -c '/usr/local/qcloud/stargate/admin/start.sh > /dev/null 2>&1 &'
47 8 * * 3 cd /root/.openclaw/workspace && /usr/bin/python3 cfm_backup.py >> /var/log/cfm_backup.log 2>&1 && /usr/bin/python3 cfm_scraper.py >> /var/log/cfm_scraper.log 2>&1
0 9 * * * /root/.openclaw/workspace/daily_health.sh >> /var/log/daily_health.log 2>&1
*/30 * * * * /root/.openclaw/workspace/weixin_health.sh >> /var/log/openclaw_weixin_health.log 2>&1
0 4 * * 1 bash /root/.openclaw/workspace/scripts/session-cleanup.sh >> /var/log/session-cleanup.log 2>&1
*/30 * * * * /root/.openclaw/scripts/momentum-trigger.sh >> /var/log/momentum-trigger.log 2>&1
*/30 * * * * cd /root/.openclaw/workspace && /usr/bin/python3 /root/.openclaw/scripts/resource-tracker.py --scan >> /var/log/resource-tracker.log 2>&1
0 * * * * /usr/bin/python3 /root/.openclaw/scripts/tracker-health-check.py >> /var/log/tracker-health.log 2>&1
*/30 * * * * /root/.openclaw/scripts/sync-dashboard-data.sh >> /var/log/dashboard-sync.log 2>&1
```

---

## 记忆系统

| 关键文件 | 状态 | 大小 | 最后修改 |
|----------|------|------|----------|
| MEMORY.md | ✅ | 8.3KB | 2026-05-18T17:57:27.039477 |
| USER.md | ✅ | 36.7KB | 2026-05-22T09:49:34.502006 |
| SOUL.md | ✅ | 6.0KB | 2026-05-20T01:23:52.630789 |
| IDENTITY.md | ✅ | 3.7KB | 2026-05-20T01:23:57.447799 |
| AGENTS.md | ✅ | 2.4KB | 2026-05-20T01:23:26.723733 |
| BOOTSTRAP.md | ✅ | 1.6KB | 2026-05-19T19:19:18.771783 |
| HEARTBEAT.md | ✅ | 2.2KB | 2026-05-22T01:16:18.393040 |

**统计**：记忆文件 27 个，日记 170 篇（最近7天 40 篇）

---

## 项目审计（四层结构）

### P0: GitHub 赚钱任务 [P0]

> 目标：通过 GitHub issue、bounty 平台获取收入  
> 健康：🟠 全面停滞 | 评分：0/10

| 项目 | 状态 | 文件数 | 最后活跃 | Blocker | 最近动作 |
|------|------|--------|----------|---------|----------|
| bounty | 🟡 stale | 5 | 62h | - | - |
| p0-github-money | 🟡 stale | 19 | 12h | - | - |

### P1: 自进化任务 [P1]

> 目标：自学习、自改进、Skill 进化与系统能力增强  
> 健康：🟡 部分停滞 | 评分：3.5/10

| 项目 | 状态 | 文件数 | 最后活跃 | Blocker | 最近动作 |
|------|------|--------|----------|---------|----------|
| hermes-lite | 🟢 active | 23 | 29h | - | - |
| p1-self-evolution | 🟡 stale | 30 | 13h | - | Cycle 6 evaluate completed. C1 CRITICAL  |

### P2: 社交网络探索 [P2]

> 目标：Agent 社交网络互动、社区建立与影响力扩展  
> 健康：🟡 部分停滞 | 评分：3.5/10

| 项目 | 状态 | 文件数 | 最后活跃 | Blocker | 最近动作 |
|------|------|--------|----------|---------|----------|
| p2-agent-social | 🟡 stale | 9 | 12h | - | ⚠️ Agent Community API 探测失败(2026-05-21 1 |
| p2-moltbook | 🟢 active | 1 | 12h | - | - |

---

## 能力验证

| 能力 | 状态 |
|------|------|
| GitHub CLI | ✅ |
| GitHub API | ✅ |
| Web 搜索 | ✅ |
| 飞书 | ❌ |
| Cloudflare Tunnel | ❌ |
| 邮件 Webhook | ✅ |

---

## 会话历史

最近会话：242 个文件

- `b700f0c3-96f9-499d-802f-9412956077ba.jsonl` (343.4KB, 0h ago)
- `69dae650-bd3c-469c-86fb-0061fb897bfe.jsonl` (1.8MB, 0h ago)
- `b1e64309-dc52-4d7d-9ab2-f74416ea9719.jsonl` (11.9KB, 0h ago)
- `32017e4a-457b-4d8f-b683-ac6c1449acf3.jsonl` (12.0KB, 0h ago)
- `88c5729f-2b33-4ca2-a0a2-558dfbfc0982.jsonl` (11.9KB, 0h ago)

---

## 模块运行状态

| 模块 | 检查通过 | 总计 | 状态 |
|------|---------|------|------|
| memory | 3 | 3 | ✅ 3/3 |
| sessions | 2 | 2 | ✅ 2/2 |
| projects | 2 | 2 | ✅ 2/2 |
| model | 3 | 4 | ✅ 3/4 |
| environment | 4 | 4 | ✅ 4/4 |
| capabilities | 4 | 6 | ✅ 4/6 |
| harness | 5 | 5 | ✅ 5/5 |

---

*报告由 P1.0 baseline-check Skill 自动生成*
