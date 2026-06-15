---
name: poisson-betting-model
title: 泊松分布足球投注模型
description: 基于泊松分布和凯利准则的足球投注模型。支持两种模式：手动交互（输入单场比赛数据）和自动管道（通过 The Odds API + football-data.org 自动抓取数据、批量预测、生成日报）。覆盖实时赔率对比、亚指分析、价值投注识别、串关建议。v2 新增：Bayesian shrinkage、杯赛/中立场检测、赛季+近期双轨加权、市场背离预警。
triggers:
  - "足球预测"
  - "投注模型"
  - "泊松分布"
  - "足球赔率分析"
  - "凯利准则"
  - "比赛预测"
  - "足球日报"
  - "自动预测"
  - "价值投注"
  - "Odds API"
  - "football-data"
  - "球探体育"
  - "百家欧指"
  - "亚指"
  - "让球盘"
  - "手动分析"
  - "预测复盘"
  - "错误分析"
  - "投注优化"
  - "泊松修正"
  - "复盘"
category: data-science
---

# 泊松分布足球投注模型

基于泊松分布建模比赛进球数，结合凯利准则做资金管理。支持手动交互和自动管道两种模式。

## 数据来源建议

- **标准 API**：The Odds API（实时赔率+赛程）+ football-data.org（历史赛果）→ 自动管道模式
- **手动数据源**：Football-Data.co.uk（免费 CSV）、OddsPortal / OddsChecker
- **非主流联赛回退**：球探体育（titan007.com）百家欧指页面 + 亚指页面 → 参见 `references/manual-analysis-fallback.md`
  - 适用于标准 API 未覆盖的联赛（中超、哥伦比亚、秘鲁等）和杯赛
  - 从页面提取最佳赔率（浏览器 console）和联赛积分数据（分析tab）
  - **⚠️ 欧指页面需会员：** `1x2.titan007.com` 显示"暂时没有本场比赛的欧指"为正常（需会员或付费解锁）。替代方案：搜索引擎搜"TeamA vs TeamB odds"或访问 oddspedia.com。亚指页面 `vip.titan007.com/AsianOdds_n.aspx` 无需会员，全部可用。
  - 亚指页面（AsianOdds_n.aspx）提供盘口变化和资金流向数据，是三信号验证的重要组成部分
- **联赛平均**：从历史数据中计算，或使用 skill 中的默认参数

## 核心方法论

### 1. 泊松分布假设

每支球队在比赛中的进球数服从泊松分布：
```
P(X = k) = (λ^k * e^(-λ)) / k!
```
其中 λ 是该队的期望进球数。

### 2. 攻防强度计算

使用历史比赛数据计算各队相对于联赛平均水平的攻防强度：

```
HomeAttStrength = Home平均进球 / 联赛平均主场进球
HomeDefStrength = Home场均失球 / 联赛平均主场失球
AwayAttStrength = Away平均进球 / 联赛平均客场进球
AwayDefStrength = Away场均失球 / 联赛平均客场失球
```

### 3. 预测期望进球

```
Home期望进球 = HomeAttStrength × AwayDefStrength × 联赛平均主场进球
Away期望进球 = AwayAttStrength × HomeDefStrength × 联赛平均客场进球
```

### 4. 比分概率矩阵

计算所有可能比分（0:0 至 5:5）的概率：
```
P(Home=i, Away=j) = Poi(Home期望, i) × Poi(Away期望, j)
```

### 5. 赛果概率

```
主胜概率 = 所有 Home > Away 的比分概率之和
平局概率 = 所有 Home = Away 的比分概率之和
客胜概率 = 所有 Home < Away 的比分概率之和
```

### 6. 凯利准则

使用凯利公式计算最优下注比例：
```
f* = (p × (odds - 1) - (1 - p)) / (odds - 1)
```
- f* = 建议下注比例（占资金百分比）
- p = 模型预测概率
- odds = 博彩公司提供的十进制赔率

凯利下注条件：仅当 p × odds > 1（正期望值）时下注。

---

## v2 模型优化（从实际失败案例推导）

2026-05-28 对两场比赛的预测全部失败后，推导出以下五处系统性优化。每个优化都针对一个具体的预测错误。

### ① Bayesian Shrinkage — 解决小样本极端估值

**失败案例：** 奇科(茨高) 的主场防守强度被算成 0.383（极强），因为主场9场仅失5球。但这是小样本（9场）导致的极端值。实际杯赛被拉尼罗斯1-0击败。

**修正：** 攻防强度向 1.0（联赛平均）收缩，样本越少收缩越强：

```python
shrinkage = min(1.0, n_games / SAMPLE_SATURATION)  # 默认饱和=15场
att_final = 1.0 + (att_raw - 1.0) * shrinkage
def_final = 1.0 + (def_raw - 1.0) * shrinkage
```

- 15场以上：不收缩（shrinkage=1.0，完全信任数据）
- 5场：只信任 5/15=33%，其余67%向平均值收缩
- 0场：完全使用平均值（1.0）

### ② 杯赛检测 — 解决联赛模型预测杯赛

**失败案例：** 哥伦杯（单场淘汰）的 0-1 低分结果。模型用的是联赛参数（平均进球1.45/1.10），杯赛防守更紧凑、偶然性更高。

**修正：** 自动检测杯赛（copa/cup/pokal/coppa/杯等关键词），降低场均进球假设：

- **国内杯赛**：场均进球 × 0.82
- **洲际杯赛**（解放者杯、欧冠等）：场均进球 × 0.90
- **国际友谊赛**：需额外注意（无FD数据时默认强度1.0，谨慎推荐）

检测逻辑：
```python
CUP_PATTERNS = [r'cup', r'copa', r'pokal', r'coppa', r'杯', ...]
def is_cup_competition(sport_key, title):  # 匹配关键词语
def is_domestic_cup(sport_key, title):    # 排除洲际赛事前缀
```

### ③ 中立场检测 — 解决虚假主场优势

**失败案例：** 水晶宫 vs 巴列卡诺在莱比锡中立场进行。模型用 PL 主场均值（1.53）给水晶宫算期望进球，夸大了主队优势。实际 1-0 但赔率1.88本身就支持水晶宫。

**修正：** Odds API 返回 `neutral_site` 字段。中立场时主客场都用客场均值：

```python
if neutral_site:
    avg_home = league_avg_away * cup_factor
    avg_away = league_avg_away * cup_factor  # 无主场优势
```

### ④ 赛季+近期双轨加权 — 解决过度依赖短期状态

**失败案例：** 巴列卡诺近10场6胜3平1负 vs 水晶宫3胜3平4负，模型给巴列卡诺43.7%概率。但巴列卡诺的"好状态"是在西甲赛季末段，对手可能无欲无求；水晶宫的"差状态"是在竞争更激烈的英超。

**修正：** 混合赛季整体和近期状态，FD API 一次获取30场，分拆计算：

```python
season_att, season_def = 全部可用比赛(最多30场)
recent_att, recent_def = 最近10场
att = 0.6 × season_att + 0.4 × recent_att
def = 0.6 × season_def + 0.4 × recent_def
```

- 赛季整体（权重0.6）：提供稳定的基准
- 近期状态（权重0.4）：反映状态变化
- 当总比赛 ≤10 场时，退化为纯赛季模式（只用全部可用数据）

### ⑤ 市场背离预警 — 防止模型过度自信

**失败案例：** 水晶宫场的赔率是 1.88/3.00/3.78，市场明显看好水晶宫。但模型给出的概率是 27.4%/28.6%/43.7%，与市场严重背离——市场隐含巴列卡诺胜率26.5%，模型给43.7%，背离17.2个百分点。这种背离本身就是模型出错的信号。

**修正：** 当模型概率与市场隐含概率背离超过阈值时标记高风险：

```python
disagreement = abs(model_prob - implied_prob)
is_high_risk = disagreement > HIGH_RISK_DISAGREEMENT  # 默认25个百分点
```

- 高风险推荐从主列表中分离，单独展示并提醒谨慎参考
- 串关建议只使用低风险推荐
- 高风险推荐排在价值推荐列表末尾

---

## 执行流程

### Step 1 — 收集输入

确认用户的输入：
1. 联赛名称（英超 / 西甲 / 德甲 / 意甲 / 法甲 / 中超等）
2. 主队名称（英文）
3. 客队名称（英文）
4. 主队近5场进球/失球数据
5. 客队近5场进球/失球数据
6. 该联赛平均主场进球数、平均客场进球数
7. 博彩公司赔率（主胜 / 平局 / 客胜 十进制赔率）

或：
1. CSV/Excel 文件路径：包含历史比赛结果 + 赔率数据

### Step 2 — 泊松预测计算

```python
from scipy.stats import poisson
import numpy as np

def predict_match(home_att, home_def, away_att, away_def, league_avg_home, league_avg_away):
    # 期望进球
    home_exp = home_att * away_def * league_avg_home
    away_exp = away_att * home_def * league_avg_away
    
    # 比分概率矩阵 (0-5)
    probs = {}
    for i in range(6):
        for j in range(6):
            probs[f"{i}:{j}"] = poisson.pmf(i, home_exp) * poisson.pmf(j, away_exp)
    
    # 赛果概率
    home_win = sum(v for k, v in probs.items() if int(k[0]) > int(k[2]))
    draw = sum(v for k, v in probs.items() if int(k[0]) == int(k[2]))
    away_win = sum(v for k, v in probs.items() if int(k[0]) < int(k[2]))
    
    return home_win, draw, away_win, home_exp, away_exp, probs
```

### Step 3 — 凯利准则计算

```python
def kelly_criterion(prob, odds, bankroll_pct=0.25):
    """
    prob: 模型预测概率 (0-1)
    odds: 十进制赔率
    bankroll_pct: 凯利分数（保守使用 0.25 即 1/4 凯利）
    """
    implied_prob = 1 / odds
    edge = prob * odds - 1
    if edge <= 0:
        return 0, "无优势，不下注"
    
    full_kelly = (prob * (odds - 1) - (1 - prob)) / (odds - 1)
    fractional_kelly = full_kelly * bankroll_pct
    
    return fractional_kelly, f"建议下注 {fractional_kelly*100:.1f}% 资金"
```

## 世界杯/国家队比赛分析

世界杯及国家队赛事与联赛有本质区别，需专门处理。

### 数据来源 — 手动模式

| 数据 | 来源 | 获取方式 |
|:----|:-----|:---------|
| 最近比赛结果 | ESPN `/soccer/team/results/_/id/{team_id}` | LightPanda goto + evaluate (document.body.innerText) |
| 亚洲盘口 | `vip.titan007.com/AsianOdds_n.aspx?id={match_id}` | LightPanda evaluate：提取表格 - 初盘盘口/即时盘口/贴水 |
| 欧洲赔率 | **搜索引擎 + 聚合站** | 球探体育百家欧指页面(`1x2.titan007.com`)需会员才显示数据，不可靠。替代：Google搜"team vs team odds" / oddspedia / Kalshi |
| 阵容伤病 | 球探体育分析页 `zq.titan007.com/analysis/{id}sb.htm` | 页面底部阵容情况段落 |
| 历史交锋 | 同上分析页 | 对赛往绩表格 |

### ⚠️ titan007 欧指页面已知问题

`1x2.titan007.com/oddslist/{id}.htm` 页面在未登录情况显示"暂时没有本场比赛的欧指"。即使有会员，数据也需动态加载。**替代方案：** 搜索引擎直接搜索比赛赔率(如"Mexico vs South Africa odds 1.42")，或访问 oddspedia.com、Kalshi.com。

已验证可用的赔率来源步骤：
1. 搜索 `mcp_anysearch_search(query="[TeamA] vs [TeamB] odds 1X2 betting", freshness="week")`
2. 从摘要中提取赔率（如 Kalshi 显示 69%/21%/11% → 隐含赔率约 1.45/4.76/9.09）
3. 或从 Goal.com / Oddspedia / Oddschecker 的搜索摘要中提取

### 攻防强度计算 — 国家队特化

**核心差异：** 国家队没有联赛式的"主客场"统计数据，因为大部分比赛是友谊赛在中立场。方法：

1. **不区分主客场进攻/防守**，使用该队全部最近比赛计算场均进/失球
2. 只有明确为该队主场（赛前标注"主"）时才使用主场基准均值
3. **Bayesian shrinkage 参数不变**（饱和15场），但国家队样本通常 <10场，收缩更强

```python
# 国家队攻防强度（无主场优势时）
# 使用全部比赛数据，不区分主客场
avg_gf = total_gf / total_games
avg_ga = total_ga / total_games

# 对世界杯，使用世界平均水平
# 历史世界杯场均：约 2.5 球/场
wc_avg_total = 2.5  # 总场均进球
wc_avg_home = 1.40  # 主场球队场均（含东道主加成）
wc_avg_away = 1.10  # 客场球队场均

# 东道主使用时：
home_exp = team_att * opponent_def * wc_avg_home * cup_factor
away_exp = opponent_att * team_def * wc_avg_away * cup_factor
```

### 世界杯特有参数

| 参数 | 数值 | 说明 |
|:----|:----:|:-----|
| 历史世界杯场均总进球 | ~2.5 | 近年趋势下降（2018:2.64, 2022:2.69） |
| 世界杯杯赛因子 | 0.90 | 洲际杯赛标准折扣 |
| 东道主揭幕战历史 | 近10届东道主首战7胜3平不败 | 极强规律，模型无法量化 |
| 东道主主场场均 | ~1.40 | 包含主场球迷+熟悉场地因素 |
| 客队场均 | ~1.10 | 不含主场优势 |

### 国家队分析已知陷阱

1. **热身赛 vs 正式赛差异** — 热身赛强度远低于世界杯正赛，使用热身赛数据可能高估/低估真实水平
2. **友谊赛阵容不可预测** — 世界杯前热身赛教练可能轮换半数主力（如2026年南非教练Broos在友谊赛轮换刚踢完洲际决赛的Sundowns球员），导致比分失真
3. **样本量极低** — 国家队年度比赛通常5-15场，Bayesian shrinkage 后攻防强度高度向1.0收缩，模型区分度有限
4. **历史交锋权重极高** — 两国国家队交手记录少，一两场的历史结果（即使是多年前的）可能承载超出统计意义的心理优势
5. **模型 vs 市场背离在本场景更常见** — 国家队数据有限导致模型不确定性高，而市场会过度反应东道主优势/大牌球星效应，背离更常见
6. **东道主效应不可量化但真实存在** — 2026世界杯墨西哥城海拔2,240米对客队体能影响巨大

---

## 赛果报告输出格式

手动分析使用**完整报告格式**（包含欧指+亚指+模型三信号），自动日报使用**简洁表格格式**。参见 `references/manual-analysis-fallback.md` 中"赛果报告输出格式"章节。

完整报告的标准结构（每次手动分析按此输出）：

简洁格式：
```markdown
# 🎯 [主队] vs [客队] 投注分析报告

## 一、数据摘要
- 联赛：[联赛名]
- 比赛日期：[日期]

## 二、球队攻防强度
| 球队 | 进攻强度 | 防守强度 |
|------|---------|---------|
| [主队] | x.xx | x.xx |
| [客队] | x.xx | x.xx |

## 三、泊松预测
| 项目 | 预测值 |
|------|--------|
| [主队]期望进球 | x.xx |
| [客队]期望进球 | x.xx |
| 最可能比分 | x:x (xx.x%) |

## 四、赛果概率
| 结果 | 模型概率 | 赔率 | 隐含概率 | 凯利建议 |
|------|---------|------|---------|---------|
| 主胜 | xx.x% | x.xx | xx.x% | xx.x% |
| 平局 | xx.x% | x.xx | xx.x% | xx.x% |
| 客胜 | xx.x% | x.xx | xx.x% | xx.x% |

## 五、凯利下注建议
- [建议下注的选项 + 比例]
- 仅下注预期价值为正的选项
```

### Step 5 — 亚指分析（手动模式下）

当手动分析中超、亚洲联赛或小众联赛时，额外进行亚指分析。亚指提供独立于欧指的市场资金流向信号。

**数据来源：** `https://vip.titan007.com/AsianOdds_n.aspx?id={match_id}`

**关键分析（titan007亚指页面提取流程）：**
1. 用LightPanda evaluate提取AsianOdds_n.aspx页面的innerText
2. 从文本中提取时间戳、盘口名、两队贴水数值
3. 对比早盘与即时盘口变化：盘口是否变动、升或降
4. 统计贴水走势：A队贴水从开盘到现在是上升还是下降
5. 寻找试盘记录：是否有短暂升或降盘后又立即回落的假动作
6. 贴水变化解读规则 - 见下方
7. 最终结论：资金方向一致指向哪一方

**贴水变化解读规则：**
- A队贴水持续下降 + B队贴水上升 = 资金流入A队
- A队贴水上升 + B队贴水下降 = 资金流入B队
- 盘口纹丝不动但贴水一方显著下降 = 盘口不变但方向明确
- 短暂试盘后立即回落 = 市场拒绝接受该盘口方向

**三信号交叉验证：** 模型概率 + 欧指走向 + 亚指变化 三个独立信号一致时才高确信度推荐。

**第四信号 — 线位变化方向（早盘 vs 即时对比）：** 当分析同一场比赛不同时间点的赔率变化时，若大小球/亚指线位向模型预测方向移动超过 ~10%（如小2.5从-110到-135，变化14%），这是独立的资金验证信号。在输出中标注"资金确认"或"线位确认"以提升置信度标记。参考案例：`references/world-cup-case-study-brazil-vs-morocco-2026.md`

**跨比赛相对校准：** 当分析多场比赛时，对比各场的升/降盘比例以校准置信度。详见 `references/manual-analysis-fallback.md` "跨比赛信号对比"和"亚指信号 vs 历史数据冲突处理"章节。

---

## 注意事项

- ⚠️ 仅供研究和教育用途，不构成投注建议
- 历史数据不保证未来表现
- 建议使用 1/4 凯利（保守）而非全凯利
- 数据量少于 5 轮比赛时预测精度显著下降
- 未考虑伤病、转会、天气等非统计因素
- 杯赛单场淘汰偶然性高，投注需比联赛更保守

### 外部因子修正

手动分析时应考虑以下外部因子，模型无法自动纳入：
> 外部因子必须输入到execute_code的Poisson计算中作为系数调整，不能仅在文字中提及。方法：定义weather_boost（天气加权）、injury_adjust（伤停加权）等变量传入calc_match函数。

| 因子 | 影响方向 | 调整建议 |

| 因子 | 影响方向 | 调整建议 |
|------|---------|---------|
| 核心球员缺阵（组织者/射手） | 攻击力下降 | 期望进球 -10%~-15% |
| 高温 >30°C | 总进球下降，对客队影响更大 | 客队期望进球额外 -5%~-10% |
| 恶劣天气（雨/雪） | 进球减少，偶然性增加 | 总体进球折扣，提高平局概率 |
| 球队扣分/场外负面 | 士气影响，通常表现低于预期 | 保守对待该队预期 |
| **大小球线位大幅移动（>10%）方向与模型一致** | **资金验证信号** | **增加置信度评级——非数值调整，而是信号确认。当线位变动与模型预测方向一致时，在最终推荐中标注"资金确认"** |

## 分析流程（用户确定的工作流）

每次手动分析必须按以下流程依次执行，不可跳过或凭感觉替代：

```
泊松模型        → 算真实概率（execute_code跑计算，不手动估算）
    ↓
凯利指数        → 算EV值（只出正EV的推荐）
    ↓
市场背离检查    → 模型概率 vs 市场隐含概率对比，背离>25%标记
    ↓
亚指线位变动    → 早盘 vs 即时盘口对比，统计升降盘家数
    ↓
大小球线位变动  → 独立资金验证信号，线位移动>10%标注"资金确认"
    ↓
基础面修正      → 伤停/历史交锋/战术/天气
```

**核心原则：** 不买市场热门的队，买市场定价错误的注（正EV）。案例：卡塔尔平局@7.07——模型29.1% vs 市场13.9%，背离34.7%，EV+105.5%。

== 凯利%强制要求 ==
凯利百分比必须出现在最终推荐的每项旁边。每次输出推荐时，凯利%单独占一列，用户需一眼看到每个选项的凯利仓位百分比。如果输出中缺少凯利%，用户会投诉。

---

### 已证实的陷阱（从实盘验证中总结）

以下陷阱来自于模型上线后的实盘验证，每个都有对应的修正措施：

1. **小样本极端估值**（奇科主场防守0.383）→ v2 添加 Bayesian shrinkage
2. **联赛参数用于杯赛**（哥伦杯当联赛算）→ v2 添加杯赛检测+进球折扣
3. **中立场虚假主场**（水晶宫在莱比锡被当主场）→ v2 添加中立字段检测
4. **短期状态过度权重**（巴列卡诺近10场6胜被放大）→ v2 添加双轨加权
5. **模型vs市场严重背离**（水晶宫场27% vs 44%）→ v2 添加背离预警
6. **FD API 固定 sleep 低效**（300秒超时）→ v2 替换为 RateLimiter 精确定时
7. **友谊赛数据不足强推**（埃及vs俄罗斯无FD数据）→ 友谊赛需手动修正且降低推荐等级
8. **排名差距过大的友谊赛押平局是陷阱**（安道尔vs伊拉克 2026-05-30）→ FIFA排名差 > 100位的友谊赛，低排名球队被进球几乎是必然事件。推荐平局相当于押注「强队全场哑火」，这个前提极脆弱。应在排名差 > 100 时自动对平局概率施加惩罚折扣（×0.6），并强制标记高风险。
9. **友谊赛必检赛前新闻：阵容完整性决定一切**（南非vs尼加拉瓜 2026-05-30）→ 南非教练Broos在赛前确认轮休所有刚打完CAF冠军联赛决赛的Sundowns球员（国家队大半主力），导致攻击力骤降，0-0闷平。赛前需检查：①近期俱乐部大赛（洲际决赛等）②教练轮换表态③世界杯/大赛前热身性质（主力可能只踢半场）。这三项信息直接影响比赛竞争强度，比任何历史数据都重要。

10. **世界杯/大赛首战保守陷阱**（海地 vs 苏格兰 2026-06-14）→ 预测大2.5但结果0-1。错误核心：误用双方全力争取3分等于开放比赛的假设判断首轮赛事。修正决策树：
    - 首战无论对手强弱，优先确保不败再争胜
    - 不容有失的合理解读是保守而非开放
    - 热身赛防守专注度远低于正赛，用热身赛大小球率预测正赛会失真
    - 首战大小球决策树：若(a)双方历史首战小球率>55%且(b)其中一队FIFA排名较低且(c)两队首战均为本届世界杯首秀，则小球权重+15%
    - 参考案例：references/world-cup-case-study-day1-2026.md

11. **多场次置信度相对校准**（连场分析 2026-06-13/14）→ 一次会话覆盖多场比赛时必须做横向信号强度对比。信号最强的1-2场作为主推单独标注，弱信号场次降级。参考案例中多场比赛置信度校准章节。

12. **极端实力差+小样本的双重收缩陷阱 + Poisson线性假设崩溃**（德国 vs 库拉索 2026-06-15）→ Bayesian shrinkage在实力悬殊且双方样本均小时严重低估实力差。德国场均3.6球(n=5)，库拉索场均失2.8球(n=4)，收缩后德国进攻从raw 3.27降至1.76(仅保留54%)，库拉索防守从raw 2.50降至1.40(仅保留44%)，实力差损失81%。**更深层问题：** Poisson的乘法线性假设在极端实力差下本身就不成立——"强很多攻×弱很多防"的乘积天然不收敛。实际德国7-1，即使收缩饱和从15降到10也只能把期望从2.44提升到3.39。修正：当同时满足(a)FIFA排名差大于70且(b)双方样本均小于8时，(i)不依赖模型进球预测作为推荐依据，(ii)市场信号（亚指线位/大小球线位变动）优先于模型输出，(iii)在报告中注明"极端实力差场景，Poisson模型可能完全失效"。

### 复盘流程

当预测失败时，按以下框架分析错误根因：

```
1. 分类：联赛 vs 杯赛 vs 友谊赛？主队 vs 中立场？有无FD数据？
2. 估值偏差：攻防强度是否被小样本扭曲？
3. 状态权重：近期状态是否掩盖了赛季基准？
4. 市场信号：模型与赔率的背离度是多少？亚指方向是否一致？
5. 外部因子：伤停/天气/场外事件是否被忽略？
6. 分类后验：这场比赛的类型（杯赛/友谊赛/联赛）是否被正确识别？
```

---

## 自动管道模式

该模型支持全自动运行模式：每天定时抓取实时数据 → 批量预测 → 生成 Markdown 日报 → 推送到飞书/微信。

### 核心脚本

位于 `~/.hermes/scripts/football-auto-predict.py`（实际运行位置），skill 目录下 `scripts/football-auto-predict.py` 是副本。

配套配置 `football.env`（`~/.hermes/scripts/`）。

### API 速率控制器

与 football-data.org 交互时必须使用 `RateLimiter` 类（内置在脚本中），不能使用固定 `time.sleep()`：

```python
class RateLimiter:
    """精确的 API 速率控制器: 确保两次调用之间至少间隔 min_interval 秒"""
    def __init__(self, min_interval=6.0):
        self.min_interval = min_interval
        self.last_call = 0.0
    
    def wait(self):
        """等待至下次可调用时间, 返回实际等待秒数"""
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()
```

**为什么不用固定 sleep？** 固定 sleep 不计算 API 调用的实际耗时（网络延迟、重试、数据处理）。当调用耗时波动时，固定 sleep 要么超速（违反限速）要么低效（浪费等待时间）。RateLimiter 自动调整。

### 数据源

| 数据源 | 用途 | 免费配额 | 注册地址 |
|--------|------|---------|---------|
| The Odds API | 实时赔率 + 赛程（upcoming matches） | 500 次/月 | the-odds-api.com |
| football-data.org | 球队历史赛果 → 攻防强度计算 | 10 次/分 | football-data.org |

### 工作流程

1. **发现联赛**: 调用 Odds API `/v4/sports/` 获取当前活跃的足球联赛（自动适应赛季更替）
2. **取赛程+赔率**: 每个联赛调用 `/v4/sports/{sport}/odds?markets=h2h`，获取 upcoming matches + 20+ 家博彩公司最佳赔率
3. **取历史赛果**: 对有 football-data.org 映射的联赛（巴甲 BSA、欧冠 CL 等），调用 `/v4/competitions/{id}/matches?status=FINISHED` 获取近 30 场赛果
4. **算攻防强度**（v2 双轨）: 从 30 场数据中拆分出赛季整体（全部）和近期（最近10场），0.6/0.4 加权，带 Bayesian shrinkage
5. **联赛上下文识别**（v2）: 检测杯赛（自动折扣进球预期）、国际友谊赛、中立场
6. **泊松预测**: 同手动模式，生成比分概率矩阵 + 赛果概率
7. **价值检测**: 对比模型概率 vs 赔率隐含概率，edge = prob × odds - 1
8. **市场背离检查**（v2）: 模型概率与市场隐含概率背离 > 25% 时标记高风险
9. **凯利下注**: 仅对 edge > MIN_EDGE（默认 3%）的非高风险选项计算凯利比例
10. **串关推荐**: 仅使用低风险推荐构建串关
11. **生成日报**: 输出结构化 Markdown，分离低风险/高风险推荐，含杯赛🏆/中立场🏟标记

### 联赛映射 (Odds API key → football-data.org code)

```
soccer_epl                      → PL  (英超)
soccer_spain_la_liga            → PD  (西甲)
soccer_germany_bundesliga       → BL1 (德甲)
soccer_italy_serie_a            → SA  (意甲)
soccer_france_ligue_one         → FL1 (法甲)
soccer_uefa_champs_league       → CL  (欧冠)
soccer_netherlands_eredivisie   → DED (荷甲)
soccer_portugal_primeira_liga   → PPL (葡超)
soccer_brazil_campeonato        → BSA (巴甲)
soccer_fifa_world_cup           → WC  (世界杯)
```

对没有 football-data.org 映射的联赛（如中超 CSL、J联赛、K联赛、挪超），自动使用联赛默认场均进球参数，不计算攻防强度。这些联赛在手动模式下通过球探体育数据源进行完整分析。

### 联赛默认场均进球

南美联赛偏高（主场 1.48-1.55），北欧联赛最高（主场 1.55-1.60，进攻开放），亚洲居中。详见 `references/auto-pipeline.md`。

中超（CSL）2026赛季：场均 ~1.35 球，主场优势明显，部分球队主场无平局。工具：`scripts/manual-poisson-calc.py` 可直接复用中超数据计算。

### Cron 部署

```python
# 脚本在 ~/.hermes/scripts/football-auto-predict.py
# 配置放 ~/.hermes/scripts/football.env

cronjob(
    action="create",
    name="足球预测日报",
    schedule="0 8 * * *",          # 每天 08:00 CST
    script="football-auto-predict.py",  # 相对 ~/.hermes/scripts/
    no_agent=True                  # 脚本 stdout 直接作为交付内容
)
```

`no_agent=True` 模式下：
- 脚本 stdout 自动推送到用户
- 零 token 消耗（无 LLM 介入）
- 空输出（无可用比赛）自动静默

⚠️ **实测运行时⏱：** 18个联赛、126场比赛约 4-5 分钟跑完（受 FD API 10次/分限速限制）。300秒 timeout 可能不够，建议用 600秒。

### 配置参数 (football.env)

```bash
ODDS_API_KEY=<your_key>       # 必填
FOOTBALL_DATA_KEY=<your_key>  # 必填
MIN_EDGE=0.03                 # 最低价值阈值（3%）
KELLY_FRACTION=0.25           # 凯利分数（1/4 保守）
BANKROLL=1000                 # 模拟本金
LEAGUES=all                   # all 或逗号分隔的联赛 key
```

### 陷阱与注意事项

- **免费配额**: Odds API 每月 500 次 + football-data.org 每分钟 10 次。每日运行消耗 ~20+ 次 Odds API + 每分钟最多10次 FD。使用 RateLimiter 自动控制频率。
- **赛季切换**: 欧洲联赛 5-8 月休赛 → 自动转到南美/亚洲/北欧联赛。脚本自动发现活跃联赛，无需手动切换。
- **FD 无数据联赛**: 世界杯（WC）在休赛期会返回空数据，但 RateLimiter 仍会等待6秒/次。30次无意义调用浪费3分钟。优化思路：检测联赛是否有已完赛数据（如先请求一次竞赛信息看 match count），如果没有则跳过整个联赛的FD处理。v2 脚本尚未实现此优化。
- **FD 队名匹配**: Odds API 和 football-data.org 的队名可能不完全一致，使用 `team_name.lower() in match_team_name.lower()` 模糊匹配。部分球队仍然匹配不上（如 Odds API 缩写 vs FD 全称），这将导致强度计算退化到默认值。
- **比赛时间窗口**: Odds API 默认返回未来 7 天内的比赛。如需更远窗口需加 `daysFrom` 参数。
- **Odds API 最佳赔率**: 使用所有 bookmaker 中各 outcome 的最大值而非平均值。平均值会更保守，但最大值更能反映市场对某个特定结果的极限定价。
- **跨联赛对比限制**: 模型在同一联赛内做攻防强度比较（相对该联赛平均）。不同联赛的球队（如英超vs西甲）无法通过攻防强度直接比较，因为强度值是相对于各自联赛均值的。对于跨联赛比赛（欧战、中立场友谊赛），模型应更依赖市场赔率而非攻防强度对比。
- **友谊赛特殊性**: 友谊赛没有联赛数据基础，模型默认强度 1.0，预测精度最低。手动分析时需额外关注：伤停（全主力？）、场地（中立/主客）、天气影响。期望值 < 3% 时不推荐。

### 支持文件

| 文件 | 用途 |
|------|------|
| `references/manual-analysis-fallback.md` | 手动分析完整流程、亚指分析、CSL参数、报告格式 |
| `references/world-cup-case-study-qatar-vs-switzerland-2026.md` | 极端背离34.7%+平局命中案例 |
| `references/world-cup-case-study-brazil-vs-morocco-2026.md` | 大小球线位移动14%确认模型案例 |
| `references/world-cup-case-study-germany-vs-curacao-2026.md` | 极端实力差+小样本双重收缩陷阱案例 |
| `references/world-cup-case-study-day1-2026.md` | 连场分析4场全赛程复盘+首战保守陷阱 |
| `references/world-cup-case-study-day2-2026.md` | 第2比赛日4场分析+亚指线位提取方法+天气/伤病系数表 |
| `references/auto-pipeline.md` | 自动管道配置参数、联赛场均进球 |
| `scripts/poisson_predict.py` | 纯 Python 泊松计算（无 scipy 依赖） |
| `scripts/manual-poisson-calc.py` | 手动分析计算器 |
| `scripts/football-auto-predict.py` | 自动管道脚本 |

### 参考

- 原始研究论文: "A Poisson Betting Model for European Soccer"
- GitHub: github.com/kushlaaaa/PoissonBettingModelSoccer
- The Odds API: the-odds-api.com
- football-data.org: football-data.org
- 球探体育 (百家欧指): op1.titan007.com
- 球探体育 (亚指): vip.titan007.com/AsianOdds_n.aspx
- 非主流联赛手动分析流程: `references/manual-analysis-fallback.md`
