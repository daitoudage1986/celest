"""
手动泊松分析计算脚本
使用球探体育(titan007.com)数据源，适用于非API联赛

用法:
  python3 scripts/manual-poisson-calc.py

导入注意：
  从 skill 目录外部（如 ~/.hermes/scripts/）调用时，不能直接 import：
    from manual_poisson_calc import poisson_pmf  ← ModuleNotFoundError
  解决：将 poisson_pmf() 和 bayesian_shrinkage() 函数复制到你的脚本中，
  或运行前添加：
    import sys; sys.path.insert(0, '~/.hermes/skills/data-science/poisson-betting-model/scripts')

输入参数（在脚本中修改）:
  - home_gf, home_ga: 主队主场进/失球数
  - home_games: 主队主场场次
  - away_gf, away_ga: 客队客场进/失球数
  - away_games: 客队客场场次
  - league_avg_home, league_avg_away: 联赛场均进/失球
  - home_odds, draw_odds, away_odds: 最佳赔率
  - recent_weight: 近期权重（默认0.4，用于双轨）
"""

import math

def poisson_pmf(k, lam):
    """泊松分布概率质量函数"""
    return (lam ** k) * math.exp(-lam) / math.factorial(k)

def bayesian_shrinkage(raw_strength, n_games, saturation=15):
    """贝叶斯收缩：小样本向1.0（联赛均值）收缩"""
    s = min(1.0, n_games / saturation)
    return 1.0 + (raw_strength - 1.0) * s

def calc_match(
    home_gf, home_ga, home_games,
    away_gf, away_ga, away_games,
    league_avg_home, league_avg_away,
    home_odds, draw_odds, away_odds,
    recent_weight=0.0,
    home_recent_att=None, home_recent_def=None,
    away_recent_att=None, away_recent_def=None,
    cup_factor=1.0,
    injury_adjust_home=0.0, injury_adjust_away=0.0
):
    """
    完整泊松比赛分析
    
    Parameters:
    - cup_factor: 杯赛折扣（国内杯0.82，洲际杯0.90，联赛1.0）
    - injury_adjust: 核心球员缺阵调整（如-0.10表示攻击力降低10%）
    """
    # 1. 原始攻防强度
    home_att_raw = (home_gf / home_games) / league_avg_home
    home_def_raw = (home_ga / home_games) / league_avg_home
    away_att_raw = (away_gf / away_games) / league_avg_away
    away_def_raw = (away_ga / away_games) / league_avg_away

    # 2. Bayesian shrinkage
    home_att = bayesian_shrinkage(home_att_raw, home_games)
    home_def = bayesian_shrinkage(home_def_raw, home_games)
    away_att = bayesian_shrinkage(away_att_raw, away_games)
    away_def = bayesian_shrinkage(away_def_raw, away_games)

    # 3. 双轨加权（如果有近期数据）
    if recent_weight > 0 and all(v is not None for v in [home_recent_att, home_recent_def, away_recent_att, away_recent_def]):
        season_w = 1 - recent_weight
        home_att = season_w * home_att + recent_weight * home_recent_att
        home_def = season_w * home_def + recent_weight * home_recent_def
        away_att = season_w * away_att + recent_weight * away_recent_att
        away_def = season_w * away_def + recent_weight * away_recent_def

    # 4. 杯赛因子 + 伤病调整
    avg_home = league_avg_home * cup_factor
    avg_away = league_avg_away * cup_factor

    home_exp = home_att * away_def * avg_home * (1 + injury_adjust_home)
    away_exp = away_att * home_def * avg_away * (1 + injury_adjust_away)

    # 5. 比分概率矩阵
    scores = {}
    for i in range(6):
        for j in range(6):
            prob = poisson_pmf(i, home_exp) * poisson_pmf(j, away_exp)
            scores[f"{i}:{j}"] = prob

    # 6. 赛果概率
    home_win_p = sum(p for (s, p) in scores.items() if int(s[0]) > int(s[2]))
    draw_p = sum(p for (s, p) in scores.items() if int(s[0]) == int(s[2]))
    away_win_p = sum(p for (s, p) in scores.items() if int(s[0]) < int(s[2]))

    # 7. 最可能比分（Top 5）
    top_scores = sorted(scores.items(), key=lambda x: -x[1])[:5]

    # 8. 凯利计算
    def kelly(prob, odds, fraction=0.25):
        edge = prob * odds - 1
        if edge <= 0:
            return 0, edge
        f = (prob * (odds - 1) - (1 - prob)) / (odds - 1)
        return f * fraction, edge

    # 9. 市场隐含概率
    total_implied = 1/home_odds + 1/draw_odds + 1/away_odds
    market_home = (1/home_odds) / total_implied
    market_draw = (1/draw_odds) / total_implied
    market_away = (1/away_odds) / total_implied

    print(f"=== 泊松分析结果 ===")
    print(f"\n期望进球：")
    print(f"  主队: {home_exp:.3f}")
    print(f"  客队: {away_exp:.3f}")
    print(f"\n攻防强度（收缩后）：")
    print(f"  主队进攻: {home_att:.3f}  主队防守: {home_def:.3f}")
    print(f"  客队进攻: {away_att:.3f}  客队防守: {away_def:.3f}")
    print(f"\n概率分布：")
    print(f"  主胜: {home_win_p*100:.1f}%")
    print(f"  平局: {draw_p*100:.1f}%")
    print(f"  客胜: {away_win_p*100:.1f}%")
    print(f"\n最可能比分：")
    for s, p in top_scores:
        print(f"  {s}: {p*100:.1f}%")
    print(f"\n价值分析：")
    for name, prob, odds in [("主胜", home_win_p, home_odds), ("平局", draw_p, draw_odds), ("客胜", away_win_p, away_odds)]:
        kelly_pct, edge = kelly(prob, odds)
        print(f"  {name}: 赔率{odds:.2f} 模型{prob*100:.1f}% 市场{1/odds/total_implied*100:.1f}% EV={edge*100:+.1f}% 凯利={kelly_pct*100:.1f}%")

    return {
        "home_exp": home_exp, "away_exp": away_exp,
        "home_win_p": home_win_p, "draw_p": draw_p, "away_win_p": away_win_p,
        "top_scores": top_scores
    }

if __name__ == "__main__":
    # ====== 在此修改参数 ======
    # 示例：辽宁铁人 vs 上海海港（2026-05-29 中超）
    calc_match(
        # 主队（辽宁）主场数据
        home_gf=8, home_ga=6, home_games=6,
        # 客队（海港）客场数据
        away_gf=5, away_ga=8, away_games=6,
        # 联赛参数
        league_avg_home=1.50, league_avg_away=1.20,
        # 最佳赔率
        home_odds=2.30, draw_odds=3.70, away_odds=2.88,
        # 伤病调整（0表示无调整）
        injury_adjust_home=0.0, injury_adjust_away=0.0,
    )
