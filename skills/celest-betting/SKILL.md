---
name: poisson-betting-model
title: 泊松分布足球投注模型
description: 基于泊松分布和凯利准则的欧洲足球投注模型。输入联赛历史比赛数据，计算各队攻防强度，预测比赛进球数和胜平负概率，结合盘口赔率输出凯利最优下注比例。
triggers:
  - "足球预测"
  - "投注模型"
  - "泊松分布"
  - "足球赔率分析"
  - "凯利准则"
  - "比赛预测"
category: data-science
---

# 泊松分布足球投注模型

基于 MIT 研究论文 "A Poisson Betting Model for European Soccer"，使用泊松分布建模比赛进球数，结合凯利准则做资金管理。

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

## 执行流程

### Step 1 — 收集输入

确认用户的输入：
1. 联赛名称（英超 / 西甲 / 德甲 / 意甲 / 法甲）
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

### Step 4 — 输出格式

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

## 数据来源建议

- **历史数据**：Football-Data.co.uk（免费 CSV 下载）
- **实时赔率**：OddsPortal / OddsChecker
- **联赛平均**：从历史数据中计算

## 注意事项

- ⚠️ 仅供研究和教育用途，不构成投注建议
- 历史数据不保证未来表现
- 建议使用 1/4 凯利（保守）而非全凯利
- 数据量少于 5 轮比赛时预测精度显著下降
- 未考虑伤病、转会、天气等非统计因素

## 参考

- 原始研究论文: "A Poisson Betting Model for European Soccer"
- GitHub: github.com/kushlaaaa/PoissonBettingModelSoccer
