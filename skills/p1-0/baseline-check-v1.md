# baseline-check v1 — P1.0 状态检查 Skill

> 目的：扫描全 workspace，生成唯一可信状态快照
> 调用时机：每次 P1.0 周期启动时、heartbeat 触发时、用户询问状态时
> 输出：JSON 或 Markdown 状态报告，写入 `state.json` 的 `last_baseline`

---

## 八步检查法

### Step 1: 目录扫描
扫描 `/root/.openclaw/workspace/` 一级目录，识别所有项目根目录。

**项目识别规则**：
- 包含 `state.json` 或 `project-status.py` 或 `README.md` 的目录
- 排除：`node_modules/`、`memory/`、`diary/`、`tmp/` 等纯数据目录
- 记录：目录名、最后修改时间、文件数量

### Step 2: 项目审计
对每个识别出的项目，检查：

```
项目名/
├── state.json          → 存在？JSON 有效？last_updated？
├── project-status.py   → 存在？可执行？
├── todo/               → 存在？文件数量？
└── 产出物              → 最近7天是否有新文件？
```

**判定规则**：
- `active`: 有 state.json 且 last_updated 在 7 天内
- `stale`: 有 state.json 但 last_updated 超过 7 天
- `orphan`: 无 state.json 但有其他项目文件
- `ghost`: 空目录或只有 README

### Step 3: 环境检查
检查 runtime 环境：

| 检查项 | 命令/方法 | 阈值 |
|--------|----------|------|
| 磁盘空间 | `df -h .` | < 80% 正常 |
| 内存 | `free -h` | < 90% 正常 |
| 负载 | `uptime` | < 5.0 正常 |
| Node.js | `node --version` | >= v20 |
| Git | `git status` | 无未提交变更=正常 |
| Cloudflare Tunnel | `curl -s localhost:PORT` | 200=正常 |

### Step 4: 记忆审计
检查记忆系统健康：

- `MEMORY.md` 存在？大小？
- `memory/` 目录下 .md 文件数量
- `USER.md` / `SOUL.md` / `IDENTITY.md` 存在？
- 最近 3 天是否有新日记写入 `diary/`

**判定**：关键文件缺失 = 红色告警；7 天无日记 = 黄色预警

### Step 5: 能力验证
验证关键外部连接：

| 能力 | 验证方式 | 备用 |
|------|---------|------|
| GitHub API | `gh auth status` | PAT 手动检查 |
| Web 搜索 | `kimi_search` 调用测试 | - |
| 飞书 | 检查 feishu token 是否有效 | - |
| 微信消息 | 最后一次消息时间 | - |

### Step 6: 历史对比
读取 `state.json` 的 `last_baseline`（如果存在），对比：

- 项目数量变化（新增/消失）
- active/stale 比例变化
- 上次告警是否已修复

### Step 7: 评分
按以下维度打分（每项 0-10）：

| 维度 | 权重 | 计算方法 |
|------|------|----------|
| 项目健康度 | 30% | active 项目数 / 总项目数 × 10 |
| 环境稳定度 | 20% | 环境检查通过项 / 总检查项 × 10 |
| 记忆完整度 | 20% | 关键文件存在且更新及时 = 10 |
| 能力可用度 | 20% | 外部连接可用数 / 总连接数 × 10 |
| 历史趋势 | 10% | 与上次 baseline 对比，变好=10，持平=5，变差=0 |

**总分 = Σ(维度分 × 权重)**

### Step 8: 报告
生成结构化输出：

```json
{
  "timestamp": "2026-05-21T22:10:00+08:00",
  "score": 7.8,
  "score_breakdown": { ... },
  "projects": {
    "total": 12,
    "active": 8,
    "stale": 2,
    "orphan": 1,
    "ghost": 1
  },
  "environment": {
    "disk": "45%",
    "memory": "72%",
    "load": "1.2",
    "nodejs": "v24.15.0",
    "git_clean": true,
    "tunnel_ok": true
  },
  "memory": {
    "MEMORY.md": "8.2KB",
    "diary_last_7d": 5,
    "critical_files_ok": true
  },
  "capabilities": {
    "github": true,
    "search": true,
    "feishu": true,
    "weixin": true
  },
  "alerts": [
    { "level": "warning", "item": "P2 stale 14d", "suggestion": "spawn 子 agent 推进" }
  ],
  "changes_since_last": {
    "new_projects": [],
    "resolved_alerts": ["context pressure"],
    "new_alerts": []
  }
}
```

---

## 输出规则

1. **默认输出 JSON**：写入 `state.json` 的 `last_baseline` 字段
2. **用户询问时**：转 Markdown 摘要，突出 alerts
3. **告警时**：精简到 3 条以内，按 severity 排序
4. **无告警时**：一句话 + 总分

---

## 调用方式

```
# 作为 P1.0 周期的一部分
python3 /root/.openclaw/workspace/skills/p1-0/baseline-check.py

# 输出
→ state.json[last_baseline] 更新
→ 如有告警，触发 report Skill
```
