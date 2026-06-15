#!/usr/bin/env python3
"""
泊松分布足球投注模型 - 可执行脚本
基于: A Poisson Betting Model for European Soccer (MIT)
"""
import math
import sys

def poisson_pmf(k, lam):
    """泊松分布概率质量函数"""
    return (lam ** k) * math.exp(-lam) / math.factorial(k)

def predict_match(home_att, home_def, away_att, away_def,
                  league_avg_home, league_avg_away):
    """
    预测单场比赛
    home_att: 主队进攻强度
    home_def: 主队防守强度
    away_att: 客队进攻强度
    away_def: 客队防守强度
    """
    home_exp = home_att * away_def * league_avg_home
    away_exp = away_att * home_def * league_avg_away

    # 比分概率矩阵 0:0 ~ 5:5
    score_probs = {}
    for i in range(6):
        for j in range(6):
            p = poisson_pmf(i, home_exp) * poisson_pmf(j, away_exp)
            score_probs[f"{i}:{j}"] = p

    home_win = sum(p for (s, p) in score_probs.items()
                   if int(s[0]) > int(s[2]))
    draw = sum(p for (s, p) in score_probs.items()
               if int(s[0]) == int(s[2]))
    away_win = sum(p for (s, p) in score_probs.items()
                   if int(s[0]) < int(s[2]))

    # 最可能比分
    most_likely = max(score_probs, key=score_probs.get)

    return {
        "home_exp": round(home_exp, 3),
        "away_exp": round(away_exp, 3),
        "home_win": round(home_win, 4),
        "draw": round(draw, 4),
        "away_win": round(away_win, 4),
        "most_likely_score": most_likely,
        "most_likely_prob": round(score_probs[most_likely], 4),
        "score_probs": {s: round(p, 4) for s, p in
                        sorted(score_probs.items(), key=lambda x: -x[1])[:10]}
    }

def kelly_criterion(prob, odds, fraction=0.25):
    """
    凯利准则
    prob: 模型预测概率
    odds: 十进制赔率
    fraction: 凯利分数（默认 1/4 保守凯利）
    """
    edge = prob * odds - 1
    if edge <= 0:
        return 0, "❌ 负期望值，不下注"

    full_kelly = (prob * (odds - 1) - (1 - prob)) / (odds - 1)
    safe_kelly = full_kelly * fraction
    return safe_kelly, f"✅ 建议下注 {safe_kelly*100:.1f}% 资金"

def calculate_team_strength(goals_for, goals_against, matches, league_avg):
    """计算球队攻防强度"""
    avg_scored = goals_for / matches if matches > 0 else 1
    avg_conceded = goals_against / matches if matches > 0 else 1
    att_strength = avg_scored / league_avg if league_avg > 0 else 1
    def_strength = avg_conceded / league_avg if league_avg > 0 else 1
    return round(att_strength, 3), round(def_strength, 3)


def main():
    # ============ 联赛默认参数 ============
    leagues = {
        "英超": {"avg_home": 1.53, "avg_away": 1.19},
        "西甲": {"avg_home": 1.48, "avg_away": 1.14},
        "德甲": {"avg_home": 1.61, "avg_away": 1.21},
        "意甲": {"avg_home": 1.52, "avg_away": 1.16},
        "法甲": {"avg_home": 1.45, "avg_away": 1.10},
    }

    print("=" * 55)
    print("  泊松分布足球投注模型 v1.0")
    print("  A Poisson Betting Model for European Soccer")
    print("=" * 55)

    # 选择联赛
    league_names = list(leagues.keys())
    print("\n可用联赛:", ", ".join(league_names))
    league = input("联赛: ").strip()
    if league not in leagues:
        print(f"⚠️ 未知联赛，使用默认参数")
        avg_home, avg_away = 1.50, 1.15
    else:
        avg_home = leagues[league]["avg_home"]
        avg_away = leagues[league]["avg_away"]

    # 主队数据
    print(f"\n--- {league} 主队信息 ---")
    home = input("主队名称: ").strip()
    home_gf = float(input("主队近5场总进球: ") or "8")
    home_ga = float(input("主队近5场总失球: ") or "4")
    home_matches = int(input("统计场次(默认5): ") or "5")

    # 客队数据
    print(f"\n--- 客队信息 ---")
    away = input("客队名称: ").strip()
    away_gf = float(input("客队近5场总进球: ") or "5")
    away_ga = float(input("客队近5场总失球: ") or "7")
    away_matches = int(input("统计场次(默认5): ") or "5")

    # 赔率
    print(f"\n--- 博彩公司赔率（十进制） ---")
    odds_h = float(input("主胜赔率: ") or "2.10")
    odds_d = float(input("平局赔率: ") or "3.40")
    odds_a = float(input("客胜赔率: ") or "3.60")

    # 计算攻防强度
    home_att, home_def = calculate_team_strength(home_gf, home_ga, home_matches, avg_home)
    away_att, away_def = calculate_team_strength(away_gf, away_ga, away_matches, avg_away)

    # 预测
    result = predict_match(home_att, home_def, away_att, away_def, avg_home, avg_away)

    # ============ 输出报告 ============
    print("\n" + "=" * 55)
    print(f"  {home} vs {away}")
    print(f"  联赛: {league}")
    print("=" * 55)

    print(f"\n📊 攻防强度")
    print(f"  {home:15s} 进攻={home_att:.3f}  防守={home_def:.3f}")
    print(f"  {away:15s} 进攻={away_att:.3f}  防守={away_def:.3f}")

    print(f"\n⚽ 泊松预测")
    print(f"  {home} 期望进球: {result['home_exp']}")
    print(f"  {away} 期望进球: {result['away_exp']}")
    print(f"  最可能比分: {result['most_likely_score']} "
          f"({result['most_likely_prob']*100:.1f}%)")

    print(f"\n📈 赛果概率 vs 赔率分析")
    outcomes = [
        ("主胜", result["home_win"], odds_h),
        ("平局", result["draw"], odds_d),
        ("客胜", result["away_win"], odds_a),
    ]
    print(f"  {'结果':6s} {'模型概率':10s} {'赔率':6s} "
          f"{'隐含概率':10s} {'期望值':8s} {'凯利建议':12s}")
    print("  " + "-" * 55)
    for name, prob, odds in outcomes:
        implied = 1 / odds
        edge = prob * odds - 1
        kelly_pct, kelly_msg = kelly_criterion(prob, odds)
        ev_str = f"+{edge*100:.1f}%" if edge > 0 else f"{edge*100:.1f}%"
        kelly_str = f"{kelly_pct*100:.1f}%" if kelly_pct > 0 else "不下注"
        print(f"  {name:6s} {prob*100:6.1f}%   {odds:<5.2f} "
              f"{implied*100:6.1f}%   {ev_str:8s} {kelly_str:>8s}")

    print(f"\n🏆 比分概率 Top 10")
    for score, prob in result["score_probs"].items():
        bar = "█" * int(prob * 100)
        print(f"  {score:5s} {prob*100:5.1f}% {bar}")

    print("\n⚠️  免责声明: 仅供研究和教育用途")
    print("    历史数据不保证未来表现")
    print("    建议使用 1/4 凯利控制风险")


if __name__ == "__main__":
    main()
