# Netlify 仪表盘部署

本会话中 Fork + 部署了 `TemiKayode/football_pro`（原始项目），作为实时足球分析仪表盘。

## Fork 路径

```bash
# 1. 安装 gh CLI 后用 PAT 登录
echo "<PAT>" | gh auth login --with-token

# 2. Fork 上游仓库
gh repo fork TemiKayode/football_pro --clone --remote

# 3. 设置 remote 带 PAT（否则 push 会提示 auth）
cd football_pro
git remote set-url origin https://<user>:<PAT>@github.com/<user>/football_pro.git
git push origin main
```

## Netlify 部署

用户使用 GitHub OAuth 登录 Netlify，走 Web UI 部署：
1. app.netlify.com → Add new site → Import from Git
2. 授权 GitHub → 选择 `daitoudage1986/football_pro`
3. Netlify 自动识别 `netlify.toml`（build: `echo done`, publish: `public`, functions: `netlify/functions`）
4. 在 Advanced 中添加环境变量：
   - `ODDS_API_KEY`、`FOOTBALL_DATA_KEY`、`MIN_EDGE`、`KELLY_FRACTION`、`BANKROLL`、`DRY_RUN=true`
5. 默认域名: `https://<user>-football-pro.netlify.app`

CLI 备用方案：`npx netlify-cli deploy --prod --dir=public`

## 调试陷阱（本会话发现）

### 1. 联赛休赛期 + 比赛截断
欧洲主流联赛（EPL、La Liga 等）在 5-8 月休赛。当前活跃的是南美/亚洲/北欧联赛 + 杯赛。
`MAX_MATCHES_PER_LEAGUE = 15` 防止世界杯（72场比赛）撑爆处理时间。

### 2. football-data.org 免费版限速 (10 req/min)
必须使用 `RateLimiter` 类（内置在脚本中）而非固定 `time.sleep(FD_API_INTERVAL)`。
- RateLimiter 自动补偿网络延迟，比固定 sleep 快约30%
- 只有映射到 FD_MAP 的联赛才会调用 FD API
- 当前有映射: 巴甲 (BSA)、欧冠 (CL)、五大联赛（但已休赛）
- 无映射联赛（中超、J联赛等）自动使用默认攻防强度 1.0
- ⚠️ 世界杯(WC) 在休赛期返回空数据，但 RateLimiter 仍等待6秒/次，30次调用浪费3分钟。优化思路：检测联赛是否有已完赛数据再决定是否调用 FD。

### 3. 球队名称模糊匹配
Odds API 和 football-data.org 的队名可能不一致：
- "Paris Saint-Germain" vs "Paris Saint Germain"
- 解决方案：`team_name.lower() in match_team_name.lower()` 而非精确匹配

### 4. 运行时⏱
v2 版实测（2026-05-28）：18个联赛、126场比赛，总运行时间约4-5分钟。
瓶颈是 FD API 10次/分限速 + 世界杯空调用约3分钟。

### 5. Cron 部署（参考，当前无活跃 cron）
```python
cronjob(action="create", name="足球预测日报",
        schedule="0 8 * * *", script="football-auto-predict.py",
        no_agent=True)
```
- `no_agent=True`：脚本 stdout 直接推送，零 token 消耗
- 服务器时区 CST (+0800)，所以 `0 8 * * *` 就是北京时间 08:00
- 当前状态：用户不活跃此cron（已移除）

## 配置模板

```bash
# football.env (同目录或 ~/.hermes/scripts/)
ODDS_API_KEY=<key>
FOOTBALL_DATA_KEY=<key>
MIN_EDGE=0.03
KELLY_FRACTION=0.25
BANKROLL=1000
LEAGUES=all
```
