# P1.0 系统状态报告

> 生成时间：2026-05-22T01:13:10.094992
> 版本：p1-baseline-v2-modular
> 工作区：/root/.openclaw/workspace

---

## 综合评分：6.5/10（B 级）

| 维度 | 得分 | 权重 | 加权 |
|------|------|------|------|
| projects | 3.3 | 30% | 0.99 |
| environment | 10 | 20% | 2.0 |
| memory | 10 | 20% | 2.0 |
| capabilities | 5.0 | 20% | 1.0 |
| trend | 5 | 10% | 0.5 |

---

## 告警清单

| 级别 | 类别 | 问题 | 建议 |
|------|------|------|------|
| 🟡 warning | project | bounty stale 54h | 检查 bounty 的 blocker 或推进 next action |
| 🟡 warning | project | p0-github-money stale 3h | 检查 p0-github-money 的 blocker 或推进 next action |
| 🟡 warning | project | p1-self-evolution stale 4h | 检查 p1-self-evolution 的 blocker 或推进 next action |
| 🟡 warning | project | p2-agent-social stale 3h | 检查 p2-agent-social 的 blocker 或推进 next action |

---

## 运行环境

```
主机：VM-13-249-ubuntu
运行时间：01:13:07 up 14 days,  8:14,  0 user,  load average: 0.34, 0.32, 0.23
磁盘：/dev/vda2        40G   29G  8.8G  77% /
内存：Mem:           7.5Gi       3.0Gi       1.2Gi       9.9Mi       3.6Gi       4.5Gi
Node.js：v24.15.0
Python：Python 3.12.3
OpenClaw：OpenClaw 2026.4.14 (323493f)
```

---

## Harness 机制

| 检查项 | 状态 |
|--------|------|
| Cron Jobs | 9 条 |
| Gateway | Service: systemd (enabled)
File logs: ~/.openclaw/logs/openclaw.log
Command: /usr/bin/node /usr/lib/node_modules/openclaw/dist/index.js gateway --port 18789
Service file: ~/.config/systemd/user/openclaw-gateway.service
Service env: OPENCLAW_GATEWAY_PORT=18789

Config (cli): ~/.openclaw/openclaw.json
Config (service): ~/.openclaw/openclaw.json

Gateway: bind=loopback (127.0.0.1), port=18789 (service args)
Probe target: ws://127.0.0.1:18789
Dashboard: http://127.0.0.1:18789/
Probe note: Loopback-only gateway; only local clients can connect.

Runtime: running (pid 1272686, state active, sub running, last exit 0, reason 0)
RPC probe: ok

Listening: 127.0.0.1:18789
Troubles: run openclaw status
Troubleshooting: https://docs.openclaw.ai/troubleshooting |
| Sessions | 238 个文件，共 139.7MB |
| Git 分支 | main |
| Git 未提交 | 有 |
| 上次提交 | 03a1c206 @ 2026-05-22 00:43:53 +0800 |

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
| USER.md | ✅ | 36.3KB | 2026-05-22T01:06:23.181739 |
| SOUL.md | ✅ | 6.0KB | 2026-05-20T01:23:52.630789 |
| IDENTITY.md | ✅ | 3.7KB | 2026-05-20T01:23:57.447799 |
| AGENTS.md | ✅ | 2.4KB | 2026-05-20T01:23:26.723733 |
| BOOTSTRAP.md | ✅ | 1.6KB | 2026-05-19T19:19:18.771783 |
| HEARTBEAT.md | ✅ | 2.0KB | 2026-05-21T21:05:26.567589 |

**统计**：记忆文件 26 个，日记 169 篇（最近7天 47 篇）

---

## 项目审计

| 项目 | Tier | 状态 | 文件数 | 最后活跃 | Blocker | 最近动作 |
|------|------|------|--------|----------|---------|----------|
| bounty | P0 | 🟡 stale | 5 | 54h | - | - |
| p0-github-money | P0 | 🟡 stale | 19 | 3h | - | - |
| p1-self-evolution | P1 | 🟡 stale | 30 | 4h | - | Cycle 6 evaluate completed. C1 CRITICAL  |
| p2-agent-social | P2 | 🟡 stale | 9 | 3h | - | ⚠️ Agent Community API 探测失败(2026-05-21 1 |
| hermes-lite | - | 🟢 active | 23 | 20h | - | - |
| p2-moltbook | - | 🟢 active | 1 | 3h | - | - |

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

最近会话：238 个文件

- `2e88f65e-d472-4f53-993c-19b06a307d6a.jsonl` (276.1KB, 0h ago)
- `bc2cd740-76ba-496f-a4b7-57338f275bc3.jsonl` (11.8KB, 0h ago)
- `69dae650-bd3c-469c-86fb-0061fb897bfe.jsonl` (1015.2KB, 0h ago)
- `0b3247d7-9458-4638-ae22-4ef9b95fe320.jsonl` (12.0KB, 0h ago)
- `bb43cc63-8cd7-4111-936f-9ec7175c12b8.jsonl` (138.5KB, 0h ago)

---

## 模块运行状态

| 模块 | 检查通过 | 总计 | 状态 |
|------|---------|------|------|
| memory | 3 | 3 | ✅ 3/3 |
| projects | 2 | 2 | ✅ 2/2 |
| sessions | 2 | 2 | ✅ 2/2 |
| model | 3 | 4 | ✅ 3/4 |
| environment | 4 | 4 | ✅ 4/4 |
| capabilities | 4 | 6 | ✅ 4/6 |
| harness | 5 | 5 | ✅ 5/5 |

---

*报告由 P1.0 baseline-check Skill 自动生成*
