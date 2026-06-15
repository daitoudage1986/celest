# 自动足球预测管道 — 部署参考

> v2 更新于 2026-05-28。属于 poisson-betting-model 技能的自动管道模式。
> 核心变更：新增 Bayesian shrinkage、杯赛/中立场检测、双轨加权、市场背离预警、RateLimiter。

## 完整联赛默认场均进球

| Odds API Key | 联赛 | 场均主 | 场均客 | FD映射 |
|-------------|------|--------|--------|--------|
| soccer_epl | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 英超 | 1.53 | 1.19 | PL |
| soccer_spain_la_liga | 🇪🇸 西甲 | 1.48 | 1.14 | PD |
| soccer_germany_bundesliga | 🇩🇪 德甲 | 1.61 | 1.21 | BL1 |
| soccer_italy_serie_a | 🇮🇹 意甲 | 1.52 | 1.16 | SA |
| soccer_france_ligue_one | 🇫🇷 法甲 | 1.45 | 1.10 | FL1 |
| soccer_uefa_champs_league | 🏆 欧冠 | 1.55 | 1.20 | CL |
| soccer_netherlands_eredivisie | 🇳🇱 荷甲 | 1.58 | 1.22 | DED |
| soccer_portugal_primeira_liga | 🇵🇹 葡超 | 1.46 | 1.12 | PPL |
| soccer_brazil_campeonato | 🇧🇷 巴甲 | 1.48 | 1.12 | BSA |
| soccer_brazil_serie_b | 🇧🇷 巴乙 | 1.40 | 1.08 | — |
| soccer_chile_campeonato | 🇨🇱 智利甲 | 1.45 | 1.10 | — |
| soccer_china_superleague | 🇨🇳 中超 | 1.55 | 1.18 | — |
| soccer_japan_j_league | 🇯🇵 J联赛 | 1.50 | 1.15 | — |
| soccer_norway_eliteserien | 🇳🇴 挪超 | 1.60 | 1.22 | — |
| soccer_sweden_allsvenskan | 🇸🇪 瑞典超 | 1.55 | 1.20 | — |
| soccer_sweden_superettan | 🇸🇪 瑞典甲 | 1.50 | 1.15 | — |
| soccer_finland_veikkausliiga | 🇫🇮 芬超 | 1.52 | 1.16 | — |
| soccer_belgium_first_div | 🇧🇪 比甲 | 1.55 | 1.18 | — |
| soccer_italy_serie_b | 🇮🇹 意乙 | 1.48 | 1.12 | — |
| soccer_spain_segunda_division | 🇪🇸 西乙 | 1.45 | 1.10 | — |
| soccer_league_of_ireland | 🇮🇪 爱超 | 1.50 | 1.15 | — |
| soccer_conmebol_copa_libertadores | 🏆 解放者杯 | 1.55 | 1.18 | — |
| soccer_conmebol_copa_sudamericana | 🏆 南球杯 | 1.50 | 1.15 | — |
| soccer_uefa_europa_conference_league | 🏆 欧协联 | 1.52 | 1.16 | — |
| soccer_fifa_world_cup | 🌍 世界杯 | 1.45 | 1.12 | WC |
| soccer_fifa_world_cup_winner | 🌍 世界杯冠军 | 1.50 | 1.15 | — |

## Odds API 关键端点

```
# 获取所有体育赛事列表
GET /v4/sports/?apiKey={key}

# 获取联赛的 upcoming matches + 赔率
GET /v4/sports/{sport_key}/odds/?apiKey={key}&regions=uk&markets=h2h&oddsFormat=decimal

# 参数说明:
#   regions=uk — 英国博彩公司（赔率最全）
#   markets=h2h — 胜平负市场
#   oddsFormat=decimal — 十进制赔率
#   默认返回未来 7 天内的比赛
```

返回数据结构关键字段：
```
[{
  "id": "game_id",
  "sport_key": "soccer_epl",
  "sport_title": "Premier League",
  "commence_time": "2026-05-28T15:00:00Z",
  "home_team": "Team A",
  "away_team": "Team B",
  "bookmakers": [{
    "title": "Bet365",
    "markets": [{
      "key": "h2h",
      "outcomes": [
        {"name": "Team A", "price": 2.10},
        {"name": "Draw", "price": 3.40},
        {"name": "Team B", "price": 3.60}
      ]
    }]
  }]
}]
```

最佳赔率提取策略：遍历所有 bookmaker 的 h2h 市场，对每个 outcome 取 max price。

## football-data.org 关键端点

```
# 获取联赛已结束比赛
GET /v4/competitions/{code}/matches?status=FINISHED&limit=N
Headers: X-Auth-Token: {key}

# 可用联赛代码 (Tier 1):
# PL, PD, BL1, SA, FL1, CL, DED, PPL, BSA, ELC, WC
```

**注意**: 免费版 football-data.org 返回的 team name 可能与 Odds API 不完全一致（例如 "Paris Saint-Germain" vs "Paris Saint Germain"）。脚本使用 `in` 模糊匹配（team_name.lower() in match_team_name.lower()）。

## 开发部署清单

1. 注册两个 API Key
2. 创建 `~/.hermes/scripts/football.env` 填入 Key
3. 放脚本到 `~/.hermes/scripts/football-auto-predict.py`（v2版，带 RateLimiter）
4. 手动测试: `cd ~/.hermes/scripts && python3 football-auto-predict.py`（~4-5分钟跑19联赛）
5. 创建 cron job:
   ```python
   cronjob(action="create", name="足球预测日报",
           schedule="0 8 * * *", script="football-auto-predict.py",
           no_agent=True)
   ```
6. 次日 08:00 验证首次自动推送

## RateLimiter 模式（重要）

所有与 football-data.org 的交互必须使用 RateLimiter 而非固定 `time.sleep()`：

```python
class RateLimiter:
    def __init__(self, min_interval=6.0):
        self.min_interval = min_interval
        self.last_call = 0.0
    def wait(self):
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
```

使用方式：
```python
limiter = RateLimiter(6.0)  # 10次/分
limiter.wait()  # 调用FD API前先wait
result = get_api_data(...)
limiter.wait()  # 下一次调用前同样wait
```

**为什么不用固定 sleep？** 固定 sleep `time.sleep(6)` 不计算 API 调用的实际耗时。当网络延迟1秒时，实际调用间隔变成7秒——慢14%。当触发重试（HTTP 429），间隔更不可控。RateLimiter 自动补偿，确保精确6秒间隔。实测从20个FD调用节省约30%总时间。

## 运行时⏱

实测数据（2026-05-28）：18个活跃联赛、126场比赛，总运行时间约4-5分钟。瓶颈主要在 football-data.org 的10次/分限速。世界杯休赛期会多出约3分钟的无效等待（WC竞赛代码无已完赛数据但 RateLimiter 仍等待）。

优化思路：在进入FD处理前先检查竞赛是否有已完赛比赛，如果没有则跳过FD调用。

## 已部署实例

- 用户：单人铁盒工厂
- 脚本: `~/.hermes/scripts/football-auto-predict.py`
- 配置: `~/.hermes/scripts/football.env`
  - ODDS_API_KEY: `0b646364085a96fe30b2ea4c14f852ed`
  - FOOTBALL_DATA_KEY: `FC9C43BF540A4CC3924360E5E9AD61CE`
- Cron job ID: `be07c8be8d36`
- 时间: 每天 08:00 CST → 推送到飞书
