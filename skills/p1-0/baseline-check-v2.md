# baseline-check v2 — P1.0 全面状态检查 Skill

> **Purpose**: 全面扫描系统状态，生成 JSON 数据包 + Markdown 报告 + HTML 可视化仪表板
> **Invocation**: 每次 P1.0 周期启动时、heartbeat 触发时、用户询问状态时
> **Architecture**: 文档(this file) + 脚本(p1-baseline.py) + 输出(JSON/Markdown/HTML)

---

## 技能组成

| 组件 | 文件 | 作用 |
|------|------|------|
| **Skill 文档** | `skills/p1-0/baseline-check-v2.md` | 本文档 — 定义检查逻辑、输出格式、调用方式 |
| **检查脚本** | `skills/p1-0/p1-baseline.py` | 执行引擎 — 收集数据、评分、生成报告 |
| **Skill 状态** | `skills/p1-0/state.json` | 记录上次检查结果和历史 |
| **输出目录** | `reports/p1-0/` | 每次运行生成 JSON + Markdown + HTML |
| **部署位置** | `p1-dashboard.html` | 主页仪表板，自动覆盖更新 |

---

## 检查范围（全面）

### 1. 模型与运行时
- 当前模型信息（从环境变量读取）
- Python / Node.js 版本
- 工作目录

### 2. Harness 机制（系统机制）
- OpenClaw Gateway 状态
- Cron Jobs 列表和数量
- Systemd 服务
- Session 文件数量和总大小
- 配置文件存在性

### 3. 记忆系统
- 关键文件完整性（MEMORY.md / USER.md / SOUL.md / IDENTITY.md / AGENTS.md / BOOTSTRAP.md / HEARTBEAT.md）
- 记忆文件数量
- 日记活跃度（最近7天）

### 4. 项目机制
- 扫描 workspace 和 projects/ 目录
- 识别所有项目（state.json / README.md / project-status.py / tiered 前缀）
- 判定状态：active / stale / orphan / ghost
- 检查 blocker、last_action

### 5. 运行环境
- 磁盘使用率
- 内存状态
- 系统负载 / 运行时间
- Git 状态（分支、未提交变更、最近提交）

### 6. 能力验证
- GitHub CLI + API
- Web 搜索（轻量检测）
- 飞书 Token
- Cloudflare Tunnel
- 邮件 Webhook

### 7. 会话历史
- 最近 10 个 session 文件
- 总 session 数量

---

## 评分算法

| 维度 | 权重 | 计算方式 |
|------|------|---------|
| 项目健康度 | 30% | active 项目数 / 总项目数 × 10 |
| 环境稳定度 | 20% | 环境检查通过项 / 总检查项 × 10 |
| 记忆完整度 | 20% | 关键文件存在 + 日记更新及时 = 10 |
| 能力可用度 | 20% | 外部连接可用数 / 总连接数 × 10 |
| 历史趋势 | 10% | 与上次 baseline 对比 |

**总分** = Σ(维度分 × 权重)，0-10 分
**评级** = A(≥8) / B(≥6) / C(≥4) / D(<4)

---

## 告警分级

| 级别 | 图标 | 响应策略 | 计划时间窗口 |
|------|------|---------|-------------|
| 🔴 critical | 红色 | 阻塞 P0 或核心能力 | 立即执行 |
| 🟡 warning | 黄色 | 可能恶化或长期停滞 | 本周期内 |
| 🟢 info | 绿色 | 值得注意但非紧急 | 下次 baseline |

---

## 输出格式

### 1. JSON 数据包 (`reports/p1-0/latest.json`)
完整结构化数据，包含 meta / score / model / environment / harness / memory_system / projects / capabilities / session_history / git / alerts

### 2. Markdown 报告 (`reports/p1-0/latest.md`)
人类可读摘要，包含评分表格、告警清单、项目审计表、环境信息

### 3. HTML 仪表板 (`p1-dashboard.html` + `reports/p1-0/latest.html`)
暗色赛博朋克主题，包含：
- 评分圆环可视化
- 告警卡片
- 项目表格
- 环境/Harness/记忆/能力四宫格
- **Skill 源码章节**（本 Skill 的 Markdown 文档和 Python 脚本源码，可折叠展开）

---

## 调用方式

```bash
# 自动运行（P1.0 周期 / heartbeat 触发）
python3 /root/.openclaw/workspace/skills/p1-0/p1-baseline.py

# 输出位置
# → reports/p1-0/latest.json
# → reports/p1-0/latest.md
# → p1-dashboard.html（主页）
# → skills/p1-0/state.json[last_baseline]
```

---

## 与其他 Skill 的关系

```
baseline-check-v2 ──→ 全面检查 + 可视化报告
       ↓
  plan-v1 ──→ 生成可执行计划
       ↓
execute-v1 ──→ 实际执行（spawn/exec）
       ↓
self-check-v1 ──→ 验证执行结果
```

---

*Version: v2 | Updated: 2026-05-22*
