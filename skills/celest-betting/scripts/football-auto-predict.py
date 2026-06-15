#!/usr/bin/env python3
"""
⚽ Football Auto-Predict — 自动足球预测日报 v2
每天定时运行：抓取赛程+赔率 → 泊松模型预测 → 价值识别 → Markdown 报告

v2 优化 (2026-05-28):
  - Bayesian shrinkage: 小样本攻防强度向默认值收缩
  - 杯赛检测: 国内杯赛自动降低场均进球预期
  - 中立场检测: 中立场取消主场优势
  - 赛季+近期双轨加权: 0.6赛季整体 + 0.4近10场
  - 市场背离预警: 模型与赔率显著背离时标记高风险

数据源:
  - The Odds API (实时赔率+赛程, 500次/月免费)
  - football-data.org (历史赛果, 10次/分免费)

配置: 环境变量或 ~/.hermes/scripts/football.env
  ODDS_API_KEY=<your_key>
  FOOTBALL_DATA_KEY=<your_key>
  MIN_EDGE=0.03           (最低价值阈值, 默认3%)
  KELLY_FRACTION=0.25     (凯利分数, 默认1/4)
  BANKROLL=1000           (模拟本金)
  LEAGUES=all             (all 或逗号分隔的联赛代码)
"""

import os
import sys
import json
import math
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# 限制：单联赛最多处理 N 场比赛 (防止世界杯等杯赛数据过大)
MAX_MATCHES_PER_LEAGUE = 15
# football-data.org API 限速: 免费版 10次/分 = 6秒/次
FD_API_INTERVAL = 6.0
# 赛季+近期双轨加权系数
SEASON_WEIGHT = 0.6
RECENT_WEIGHT = 0.4
# Bayesian shrinkage 饱和样本数 (>=此值则不再收缩)
SAMPLE_SATURATION = 15
# 市场背离预警阈值
HIGH_RISK_DISAGREEMENT = 0.25
# 杯赛场均进球折扣系数
CUP_GOALS_FACTOR = 0.82

# ─── 配置 ─────────────────────────────────────────────────

ENV_FILE = os.path.expanduser("~/.hermes/scripts/football.env")


def load_config():
    """从环境变量 + .env 文件加载配置"""
    config = {}
    env_path = ENV_FILE
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
    for key in ["ODDS_API_KEY", "FOOTBALL_DATA_KEY", "MIN_EDGE",
                 "KELLY_FRACTION", "BANKROLL", "LEAGUES"]:
        env_val = os.environ.get(key)
        if env_val:
            config[key] = env_val
    return config


# football-data.org T1 联赛映射 (Odds API key → FD competition code)
FD_MAP = {
    "soccer_epl":                      "PL",
    "soccer_spain_la_liga":            "PD",
    "soccer_germany_bundesliga":       "BL1",
    "soccer_italy_serie_a":            "SA",
    "soccer_france_ligue_one":         "FL1",
    "soccer_uefa_champs_league":       "CL",
    "soccer_netherlands_eredivisie":   "DED",
    "soccer_portugal_primeira_liga":   "PPL",
    "soccer_brazil_campeonato":        "BSA",
    "soccer_fifa_world_cup":           "WC",
}

# ─── 杯赛检测 ──────────────────────────────────────────────

# 杯赛关键词 (用于从 sport_key 和 title 检测)
CUP_PATTERNS = [
    r'cup', r'copa', r'pokal', r'coppa', r'coupe',
    r'fa_', r'dfb', r'league_cup',
    # 中文
    r'杯', r'协',
]

def is_cup_competition(sport_key, title=""):
    """检测是否杯赛"""
    check_str = f"{sport_key} {title}".lower()
    return any(re.search(p, check_str) for p in CUP_PATTERNS)

def is_domestic_cup(sport_key, title=""):
    """检测是否国内杯赛 (vs 洲际杯赛)"""
    check_str = f"{sport_key} {title}".lower()
    # 国内杯赛: 不含 uefa/conmebol/concacaf/afc/caf 等洲际前缀
    continental = [r'uefa', r'conmebol', r'concacaf', r'afc_', r'caf_', r'ofc_',
                   r'europa', r'champions', r'libertadores', r'sudamericana',
                   r'nations_league', r'european']
    is_continental = any(re.search(p, check_str) for p in continental)
    is_cup = any(re.search(p, check_str) for p in CUP_PATTERNS)
    return is_cup and not is_continental

def is_neutral_site(match):
    """检测是否中立场"""
    return match.get("neutral_site", False)


# 联赛默认场均进球 (用于没有 football-data 数据的联赛)
# 按地理/风格分组的估算值
DEFAULT_AVG = {"home": 1.50, "away": 1.15}

# 联赛特定默认值 (基于历史统计)
LEAGUE_DEFAULTS = {
    # 南美
    "soccer_brazil_campeonato":            {"home": 1.48, "away": 1.12},
    "soccer_brazil_serie_b":               {"home": 1.40, "away": 1.08},
    "soccer_chile_campeonato":             {"home": 1.45, "away": 1.10},
    "soccer_argentina_primera_division":   {"home": 1.42, "away": 1.08},
    "soccer_conmebol_copa_libertadores":   {"home": 1.55, "away": 1.18},
    "soccer_conmebol_copa_sudamericana":   {"home": 1.50, "away": 1.15},
    # 亚洲
    "soccer_china_superleague":            {"home": 1.55, "away": 1.18},
    "soccer_japan_j_league":               {"home": 1.50, "away": 1.15},
    # 北欧
    "soccer_norway_eliteserien":           {"home": 1.60, "away": 1.22},
    "soccer_sweden_allsvenskan":           {"home": 1.55, "away": 1.20},
    "soccer_sweden_superettan":            {"home": 1.50, "away": 1.15},
    "soccer_finland_veikkausliiga":        {"home": 1.52, "away": 1.16},
    # 欧洲其他
    "soccer_belgium_first_div":            {"home": 1.55, "away": 1.18},
    "soccer_italy_serie_b":                {"home": 1.48, "away": 1.12},
    "soccer_spain_segunda_division":       {"home": 1.45, "away": 1.10},
    "soccer_league_of_ireland":            {"home": 1.50, "away": 1.15},
    "soccer_uefa_europa_conference_league": {"home": 1.52, "away": 1.16},
    "soccer_uefa_champs_league":           {"home": 1.55, "away": 1.20},
    # 国际赛事
    "soccer_fifa_world_cup":               {"home": 1.45, "away": 1.12},
    "soccer_fifa_world_cup_winner":        {"home": 1.50, "away": 1.15},
}

# 联赛中文名
LEAGUE_CN = {
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 英超",
    "soccer_spain_la_liga": "🇪🇸 西甲",
    "soccer_germany_bundesliga": "🇩🇪 德甲",
    "soccer_italy_serie_a": "🇮🇹 意甲",
    "soccer_france_ligue_one": "🇫🇷 法甲",
    "soccer_uefa_champs_league": "🏆 欧冠",
    "soccer_netherlands_eredivisie": "🇳🇱 荷甲",
    "soccer_portugal_primeira_liga": "🇵🇹 葡超",
    "soccer_brazil_campeonato": "🇧🇷 巴甲",
    "soccer_brazil_serie_b": "🇧🇷 巴乙",
    "soccer_chile_campeonato": "🇨🇱 智利甲",
    "soccer_china_superleague": "🇨🇳 中超",
    "soccer_japan_j_league": "🇯🇵 J联赛",
    "soccer_norway_eliteserien": "🇳🇴 挪超",
    "soccer_sweden_allsvenskan": "🇸🇪 瑞典超",
    "soccer_sweden_superettan": "🇸🇪 瑞典甲",
    "soccer_finland_veikkausliiga": "🇫🇮 芬超",
    "soccer_belgium_first_div": "🇧🇪 比甲",
    "soccer_italy_serie_b": "🇮🇹 意乙",
    "soccer_spain_segunda_division": "🇪🇸 西乙",
    "soccer_league_of_ireland": "🇮🇪 爱超",
    "soccer_conmebol_copa_libertadores": "🏆 解放者杯",
    "soccer_conmebol_copa_sudamericana": "🏆 南球杯",
    "soccer_uefa_europa_conference_league": "🏆 欧协联",
    "soccer_fifa_world_cup": "🌍 世界杯",
    "soccer_fifa_world_cup_winner": "🌍 世界杯冠军",
}


# ─── HTTP 工具 ─────────────────────────────────────────────

def api_get(url, headers=None, retries=2):
    """带重试的 GET 请求"""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.code != 429 else ""
            if e.code == 429 and attempt < retries:
                wait = 5 * (attempt + 1)
                time.sleep(wait)
                continue
            return {"error": f"HTTP {e.code}: {body[:200]}"}
        except Exception as e:
            if attempt < retries:
                time.sleep(3)
                continue
            return {"error": str(e)}
    return {"error": "max retries exceeded"}


# ─── API 速率控制器 ─────────────────────────────────────────

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
            wait_time = self.min_interval - elapsed
            time.sleep(wait_time)
            waited = wait_time
        else:
            waited = 0
        self.last_call = time.time()
        return round(waited, 2)


# ─── 泊松预测模型 ──────────────────────────────────────────

def poisson_pmf(k, lam):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def predict_match(home_att, home_def, away_att, away_def,
                  league_avg_home, league_avg_away,
                  neutral_site=False, cup_factor=1.0):
    """
    泊松预测比赛
    - neutral_site=True: 主客场都用 away 均值 (无主场优势)
    - cup_factor: 杯赛场均进球折扣 (如 0.82)
    """
    if neutral_site:
        # 中立场：主客场都用联赛客场均值
        avg_h = league_avg_away * cup_factor
        avg_a = league_avg_away * cup_factor
    else:
        avg_h = league_avg_home * cup_factor
        avg_a = league_avg_away * cup_factor

    home_exp = home_att * away_def * avg_h
    away_exp = away_att * home_def * avg_a

    score_probs = {}
    for i in range(6):
        for j in range(6):
            p = poisson_pmf(i, home_exp) * poisson_pmf(j, away_exp)
            score_probs[f"{i}:{j}"] = p

    home_win = sum(p for (s, p) in score_probs.items() if int(s[0]) > int(s[2]))
    draw = sum(p for (s, p) in score_probs.items() if int(s[0]) == int(s[2]))
    away_win = sum(p for (s, p) in score_probs.items() if int(s[0]) < int(s[2]))
    most_likely = max(score_probs, key=score_probs.get)
    return {
        "home_exp": round(home_exp, 3),
        "away_exp": round(away_exp, 3),
        "home_win": round(home_win, 4),
        "draw": round(draw, 4),
        "away_win": round(away_win, 4),
        "most_likely_score": most_likely,
        "most_likely_prob": round(score_probs[most_likely], 4),
        "score_probs": {s: round(p, 4)
                        for s, p in sorted(score_probs.items(), key=lambda x: -x[1])[:5]},
        "neutral": neutral_site,
        "cup_factor": cup_factor,
    }


def kelly_criterion(prob, odds, fraction=0.25):
    edge = prob * odds - 1
    if edge <= 0:
        return 0, edge
    full_kelly = (prob * (odds - 1) - (1 - prob)) / (odds - 1)
    safe_kelly = full_kelly * fraction
    return round(safe_kelly, 4), round(edge, 4)


# ─── 数据获取 ──────────────────────────────────────────────

def get_active_soccer_leagues(odds_key):
    """从 Odds API 获取活跃的足球联赛列表"""
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={odds_key}"
    data = api_get(url)
    if isinstance(data, dict) and "error" in data:
        return {"error": data["error"]}
    soccer = [s for s in data
              if s.get("group", "").lower() == "soccer" and s.get("active")]
    return soccer


def get_upcoming_matches(odds_key, sport_key):
    """获取某联赛的 upcoming matches + 赔率"""
    url = (f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
           f"?apiKey={odds_key}&regions=uk&markets=h2h&oddsFormat=decimal")
    data = api_get(url)
    if isinstance(data, dict) and "error" in data:
        return []
    return data if isinstance(data, list) else []


def get_team_recent_matches(fd_key, fd_comp_id, team_name, limit=10):
    """从 football-data.org 获取球队近期赛果"""
    url = (f"https://api.football-data.org/v4/competitions/"
           f"{fd_comp_id}/matches?status=FINISHED&limit={limit}")
    headers = {"X-Auth-Token": fd_key}
    data = api_get(url, headers=headers)
    if isinstance(data, dict) and "error" in data:
        return None

    matches = data.get("matches", [])
    team_matches = []
    names_to_check = [team_name.lower()]

    for m in matches:
        h = m.get("homeTeam", {}).get("name", "")
        a = m.get("awayTeam", {}).get("name", "")
        score = m.get("score", {})
        ft = score.get("fullTime", {})
        hg = ft.get("home")
        ag = ft.get("away")
        if hg is None or ag is None:
            continue

        hl = h.lower()
        al = a.lower()
        is_home = any(n in hl for n in names_to_check)
        is_away = any(n in al for n in names_to_check)

        if is_home:
            team_matches.append({"home": True, "gf": hg, "ga": ag, "opponent": a})
        elif is_away:
            team_matches.append({"home": False, "gf": ag, "ga": hg, "opponent": h})

    return team_matches[-limit:]


# ─── 攻防强度计算 (v2: 加入 Bayesian shrinkage) ────────────

def calculate_team_strength(matches, league_avg_home, league_avg_away,
                            sample_saturation=SAMPLE_SATURATION):
    """
    从近期赛果计算攻防强度, 带 Bayesian shrinkage:
    - 样本越少, 强度越向 1.0 (联赛平均) 收缩
    - sample_saturation: 达到此样本数后不再收缩 (默认15场)
    """
    if not matches:
        return 1.0, 1.0, 0

    home_games = [m for m in matches if m["home"]]
    away_games = [m for m in matches if not m["home"]]

    if home_games:
        avg_gf = sum(m["gf"] for m in home_games) / len(home_games)
        avg_ga = sum(m["ga"] for m in home_games) / len(home_games)
        att_raw = avg_gf / league_avg_home if league_avg_home > 0 else 1.0
        def_raw = avg_ga / league_avg_home if league_avg_home > 0 else 1.0
        games = len(home_games)
    elif away_games:
        avg_gf = sum(m["gf"] for m in away_games) / len(away_games)
        avg_ga = sum(m["ga"] for m in away_games) / len(away_games)
        att_raw = avg_gf / league_avg_away if league_avg_away > 0 else 1.0
        def_raw = avg_ga / league_avg_away if league_avg_away > 0 else 1.0
        games = len(away_games)
    else:
        return 1.0, 1.0, 0

    # Bayesian shrinkage: 样本越小越向1.0收缩
    shrinkage = min(1.0, games / sample_saturation)
    att = 1.0 + (att_raw - 1.0) * shrinkage
    deff = 1.0 + (def_raw - 1.0) * shrinkage

    return round(att, 3), round(deff, 3), games


def get_team_strength_blended(fd_key, fd_comp_id, team_name,
                               league_avg_home, league_avg_away):
    """
    赛季+近期双轨加权计算攻防强度:
    - 获取最近30场作为赛季样本
    - 最近10场作为近期状态
    - 加权: SEASON_WEIGHT(0.6) × 赛季 + RECENT_WEIGHT(0.4) × 近期
    - 均带 Bayesian shrinkage
    """
    all_matches = get_team_recent_matches(fd_key, fd_comp_id, team_name, limit=30)
    if all_matches is None:
        return None, None, 0, True

    if not all_matches:
        return 1.0, 1.0, 0, True  # uses_default_strength = True

    n_total = len(all_matches)

    if n_total <= 10:
        # 样本太少，无法做双轨，直接用全部(带shrinkage)
        att, deff, _ = calculate_team_strength(all_matches, league_avg_home, league_avg_away)
        return att, deff, n_total, False

    # 赛季整体: 全部可用比赛
    season_att, season_def, _ = calculate_team_strength(all_matches, league_avg_home, league_avg_away)
    # 近期状态: 最近10场
    recent_matches = all_matches[-10:]
    recent_att, recent_def, _ = calculate_team_strength(recent_matches, league_avg_home, league_avg_away)

    # 加权 blend
    att = season_att * SEASON_WEIGHT + recent_att * RECENT_WEIGHT
    deff = season_def * SEASON_WEIGHT + recent_def * RECENT_WEIGHT

    return round(att, 3), round(deff, 3), n_total, False


# ─── 工具函数 ──────────────────────────────────────────────

def format_time(utc_str):
    """UTC 时间 → 北京时间"""
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        cst = dt + timedelta(hours=8)
        return cst.strftime("%m-%d %H:%M")
    except:
        return utc_str[:16]


def fmt_prob(p):
    """格式化概率"""
    return f"{p*100:.1f}%"


# ─── 核心流程 ──────────────────────────────────────────────

def main():
    config = load_config()
    odds_key = config.get("ODDS_API_KEY", "").strip()
    fd_key = config.get("FOOTBALL_DATA_KEY", "").strip()

    missing = []
    if not odds_key:
        missing.append("ODDS_API_KEY")
    if not fd_key:
        missing.append("FOOTBALL_DATA_KEY")
    if missing:
        print(f"❌ 缺少配置: {', '.join(missing)}")
        print(f"请编辑 {ENV_FILE} 填入 Key")
        sys.exit(1)

    min_edge = float(config.get("MIN_EDGE", "0.03"))
    kelly_frac = float(config.get("KELLY_FRACTION", "0.25"))
    bankroll = float(config.get("BANKROLL", "1000"))

    # ── Step 1: 发现当前活跃的足球联赛 ──
    print("📍 正在发现活跃联赛...", file=sys.stderr)
    leagues = get_active_soccer_leagues(odds_key)

    if isinstance(leagues, dict) and "error" in leagues:
        print(f"❌ Odds API 错误: {leagues['error']}", file=sys.stderr)
        sys.exit(1)

    # 筛选用户指定的联赛
    leagues_filter = config.get("LEAGUES", "all").strip()
    if leagues_filter.lower() != "all":
        filter_set = set(l.strip() for l in leagues_filter.split(","))
        leagues = [l for l in leagues if l["key"] in filter_set]

    if not leagues:
        print("⚠️ 没有活跃的足球联赛", file=sys.stderr)
        sys.exit(0)

    print(f"✅ 发现 {len(leagues)} 个活跃联赛", file=sys.stderr)

    # ── API 速率控制器 ──
    fd_limiter = RateLimiter(FD_API_INTERVAL)

    # ── Step 2: 遍历每个联赛，获取比赛+赔率 ──
    all_predictions = []
    value_picks = []
    league_stats = {}

    for league in leagues:
        sport_key = league["key"]
        league_title = league.get("title", sport_key)
        league_name = LEAGUE_CN.get(sport_key, league_title)
        avg_home = LEAGUE_DEFAULTS.get(sport_key, {}).get("home", DEFAULT_AVG["home"])
        avg_away = LEAGUE_DEFAULTS.get(sport_key, {}).get("away", DEFAULT_AVG["away"])
        has_fd = sport_key in FD_MAP
        fd_comp_id = FD_MAP.get(sport_key)

        # ── 杯赛检测 ──
        is_cup = is_cup_competition(sport_key, league_title)
        is_domestic = is_domestic_cup(sport_key, league_title)
        cup_factor = CUP_GOALS_FACTOR if is_domestic else (0.90 if is_cup else 1.0)
        league_tags = []
        if is_cup:
            league_tags.append("🏆杯赛")

        # 获取 upcoming matches
        matches = get_upcoming_matches(odds_key, sport_key)

        # 检查剩余配额
        if isinstance(matches, dict) and "error" in matches:
            print(f"   ⚠️ {league_name}: {matches['error'][:60]}", file=sys.stderr)
            continue

        if not matches:
            continue

        # 截断到最大场次 (防止杯赛超量)
        if len(matches) > MAX_MATCHES_PER_LEAGUE:
            print(f"   ⚠️ 截断到 {MAX_MATCHES_PER_LEAGUE} 场 (原 {len(matches)} 场)", file=sys.stderr)
            matches = matches[:MAX_MATCHES_PER_LEAGUE]

        print(f"   📋 {league_name}: {len(matches)} 场比赛{' ' + ''.join(league_tags) if league_tags else ''}", file=sys.stderr)
        league_data = []

        for match in matches:
            home = match.get("home_team", "")
            away = match.get("away_team", "")
            commence = match.get("commence_time", "")
            if not home or not away:
                continue

            # ── 中立场检测 ──
            neutral = is_neutral_site(match)
            match_tags = []
            if neutral:
                match_tags.append("中立场")

            # 提取赔率 (最佳赔率)
            best_odds = {}
            for bm in match.get("bookmakers", []):
                for market in bm.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            name = outcome.get("name", "")
                            price = outcome.get("price", 0)
                            if name == home:
                                best_odds["home_win"] = max(best_odds.get("home_win", 0), price)
                            elif name == away:
                                best_odds["away_win"] = max(best_odds.get("away_win", 0), price)
                            elif name == "Draw":
                                best_odds["draw"] = max(best_odds.get("draw", 0), price)

            if not best_odds.get("home_win"):
                continue

            # ── 获取攻防强度 (v2: 双轨加权 + Shrinkage) ──
            home_att = home_def = 1.0
            away_att = away_def = 1.0
            home_games = away_games = 0
            uses_default_strength = True

            if has_fd and fd_comp_id:
                fd_limiter.wait()
                h_result = get_team_strength_blended(fd_key, fd_comp_id, home, avg_home, avg_away)
                fd_limiter.wait()
                a_result = get_team_strength_blended(fd_key, fd_comp_id, away, avg_home, avg_away)

                if h_result is not None and a_result is not None:
                    h_att, h_def, h_g, h_default = h_result
                    a_att, a_def, a_g, a_default = a_result
                    if not h_default or not a_default:
                        home_att, home_def, home_games = h_att, h_def, h_g
                        away_att, away_def, away_games = a_att, a_def, a_g
                        uses_default_strength = h_default or a_default

            # ── 泊松预测 (v2: 传入中立场 + 杯赛因子) ──
            pred = predict_match(
                home_att, home_def,
                away_att, away_def,
                avg_home, avg_away,
                neutral_site=neutral,
                cup_factor=cup_factor,
            )

            # ── 价值检测 ──
            match_value = False
            value_tip = None
            value_odds = 0
            for tip_key, tip_label in [("home_win", "主胜"), ("draw", "平局"), ("away_win", "客胜")]:
                prob = pred.get(tip_key, 0)
                odds_val = best_odds.get(tip_key, 0)
                if odds_val <= 0:
                    continue
                edge_val = prob * odds_val - 1
                if edge_val > min_edge:
                    match_value = True
                    kelly_pct, _ = kelly_criterion(prob, odds_val, kelly_frac)

                    # ── 市场背离检测 (v2) ──
                    implied_prob = 1 / odds_val
                    disagreement = abs(prob - implied_prob)
                    is_high_risk = disagreement > HIGH_RISK_DISAGREEMENT

                    value_picks.append({
                        "league": league_name[:4],
                        "home": home,
                        "away": away,
                        "tip": tip_label,
                        "model_prob": prob,
                        "odds": odds_val,
                        "implied": implied_prob,
                        "edge": edge_val,
                        "kelly": kelly_pct,
                        "is_high_risk": is_high_risk,
                        "disagreement": round(disagreement, 3),
                        "neutral": neutral,
                        "is_cup": is_cup,
                    })
                    if not value_tip:
                        value_tip = tip_key
                        value_odds = odds_val

            league_data.append({
                "league": league_name,
                "home_team": home,
                "away_team": away,
                "kickoff": format_time(commence),
                "home_att": home_att,
                "home_def": home_def,
                "home_games": home_games,
                "away_att": away_att,
                "away_def": away_def,
                "away_games": away_games,
                "odds_home_win": best_odds.get("home_win", 0),
                "odds_draw": best_odds.get("draw", 0),
                "odds_away_win": best_odds.get("away_win", 0),
                "prediction": pred,
                "is_value": match_value,
                "value_tip": value_tip,
                "value_odds": value_odds,
                "uses_default_strength": uses_default_strength,
                "neutral": neutral,
                "is_cup": is_cup,
                "cup_factor": cup_factor,
                "tags": match_tags,
            })

        if league_data:
            all_predictions.append({"league_key": sport_key, "league_name": league_name, "data": league_data})
            league_stats[league_name] = len(league_data)
            if league_tags:
                all_predictions[-1]["tags"] = league_tags

    # 价值推荐按期望值排序, 高风险排后面
    value_picks.sort(key=lambda x: (1 if x["is_high_risk"] else 0, -x["edge"]))
    total_matches = sum(league_stats.values())

    # ── Step 3: 生成报告 ──
    if total_matches == 0:
        print("📭 当前没有可预测的比赛", file=sys.stderr)
        print("常见原因: 主要联赛休赛期，或所有比赛都在 48h 以后")
        sys.exit(0)

    now = datetime.now(timezone(timedelta(hours=8)))
    lines = []
    lines.append("# ⚽ 足球预测日报 v2")
    lines.append("")
    lines.append(f"📅 **{now.strftime('%Y-%m-%d %H:%M')}** 北京时间")
    lines.append(f"📊 覆盖 {len(league_stats)} 个联赛 · {total_matches} 场比赛")
    lines.append(f"📡 数据源: The Odds API + football-data.org")
    lines.append("")
    lines.append("> 🛠 **v2 优化已生效:** Bayesian shrinkage · 杯赛参数 · 中立场检测 · 赛季+近期双轨 · 市场背离预警")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── 价值推荐 TOP ──
    if value_picks:
        lines.append("## 🎯 今日价值推荐")
        lines.append("")

        # 先筛选出非高风险推荐
        safe_picks = [p for p in value_picks if not p["is_high_risk"]]
        high_risk_picks = [p for p in value_picks if p["is_high_risk"]]

        if safe_picks:
            lines.append("### ✅ 低风险价值推荐 (市场一致)")
            lines.append("")
            lines.append("| # | 联赛 | 比赛 | 推荐 | 模型概率 | 赔率 | 隐含概率 | 期望值 | 凯利 |")
            lines.append("|---|------|------|------|---------|------|---------|-------|------|")
            for i, p in enumerate(safe_picks[:5], 1):
                tag = ""
                if p["neutral"]:
                    tag += " 🏟中"
                if p.get("is_cup"):
                    tag += " 🏆"
                lines.append(
                    f"| {i} | {p['league']}{tag} | **{p['home']} vs {p['away']}** "
                    f"| **{p['tip']}** | {fmt_prob(p['model_prob'])} "
                    f"| {p['odds']:.2f} | {fmt_prob(p['implied'])} "
                    f"| **+{p['edge']*100:.1f}%** | {p['kelly']*100:.1f}% |")
            lines.append("")

        if high_risk_picks:
            lines.append("### ⚠️ 高风险价值推荐 (模型vs市场显著背离)")
            lines.append("")
            lines.append("> ⚠️ 以下推荐模型概率与市场赔率背离超过阈值，建议谨慎参考")
            lines.append("")
            lines.append("| # | 联赛 | 比赛 | 推荐 | 模型概率 | 赔率 | 隐含概率 | 背离度 | 期望值 |")
            lines.append("|---|------|------|------|---------|------|---------|-------|-------|")
            for i, p in enumerate(high_risk_picks[:5], 1):
                tag = ""
                if p["neutral"]:
                    tag += " 🏟中"
                if p.get("is_cup"):
                    tag += " 🏆"
                lines.append(
                    f"| {i} | {p['league']}{tag} | **{p['home']} vs {p['away']}** "
                    f"| **{p['tip']}** | {fmt_prob(p['model_prob'])} "
                    f"| {p['odds']:.2f} | {fmt_prob(p['implied'])} "
                    f"| **{p['disagreement']*100:.0f}pp** | +{p['edge']*100:.1f}% |")
            lines.append("")

        if safe_picks:
            # 累加器建议 (仅限低风险)
            lines.append("### 🔗 串关建议")
            lines.append("")
            top3 = safe_picks[:3]
            if len(top3) >= 2:
                combo_odds = 1.0
                parts = []
                for p in top3:
                    combo_odds *= p["odds"]
                    parts.append(f"{p['tip']}(@{p['odds']:.2f})")
                lines.append(f"- **{len(top3)}串1**: {' + '.join(parts)}")
                lines.append(f"- 组合赔率: **{combo_odds:.2f}**")
                stake = bankroll * 0.05
                lines.append(f"- 建议本金: {stake:.0f} 元 (bankroll 5%)")
                lines.append("")

        lines.append("---")
        lines.append("")

    # ── 各联赛详细报告 ──
    lines.append("## 📊 联赛详情")
    lines.append("")

    for section in all_predictions:
        league_name = section["league_name"]
        matches = section["data"]
        tags = section.get("tags", [])
        tag_str = " " + " ".join(tags) if tags else ""
        lines.append(f"### {league_name}{tag_str} ({len(matches)}场)")
        lines.append("")

        for m in matches:
            home = m["home_team"]
            away = m["away_team"]
            pred = m["prediction"]
            kt = m.get("kickoff", "?")
            tags = m.get("tags", [])
            tag_str = " · " + " · ".join(tags) if tags else ""

            lines.append(f"**⚡ {home} vs {away}** · 🕐 {kt}{tag_str}")
            lines.append("")

            # 攻防强度
            has_data = m["home_games"] > 0 or m["away_games"] > 0
            if has_data:
                lines.append(f"| 球队 | 进攻强度 | 防守强度 | 分析场次 | 数据来源 |")
                lines.append(f"|------|---------|---------|---------|---------|")
                blend_tag = "赛季+近期双轨" if m["home_games"] > 10 else ""
                lines.append(f"| {home} | {m['home_att']} | {m['home_def']} | {m['home_games']}场 | {blend_tag} |")
                blend_tag = "赛季+近期双轨" if m["away_games"] > 10 else ""
                lines.append(f"| {away} | {m['away_att']} | {m['away_def']} | {m['away_games']}场 | {blend_tag} |")
            else:
                lines.append("> 📊 无历史数据，使用联赛默认攻防强度")
                lines.append("")

            # 预测参数提示
            params = []
            if pred.get("neutral"):
                params.append("中立场(无主优)")
            if pred.get("cup_factor", 1.0) < 1.0:
                params.append(f"杯赛因子×{pred['cup_factor']}")
            if params:
                lines.append(f"> ⚙️ 参数: {' · '.join(params)}")
                lines.append("")

            # 泊松预测
            lines.append(f"> ⚽ **泊松模型:** {home} {pred['home_exp']} — {pred['away_exp']} {away}")
            lines.append(f"> 最可能比分: **{pred['most_likely_score']}** ({fmt_prob(pred['most_likely_prob'])})")
            lines.append("")

            # 赛果概率 vs 赔率
            lines.append(f"| 结果 | 模型概率 | 赔率 | 隐含概率 | 期望值 | 凯利 | 风险 |")
            lines.append(f"|------|---------|------|---------|-------|------|------|")
            for tip_key, tip_label in [("home_win", "主胜"), ("draw", "平局"), ("away_win", "客胜")]:
                prob = pred.get(tip_key, 0)
                odds_val = m.get(f"odds_{tip_key}", 0)
                if odds_val <= 0:
                    continue
                implied = 1 / odds_val
                kelly_pct, kelly_edge = kelly_criterion(prob, odds_val, kelly_frac)
                edge_str = f"+{kelly_edge*100:.1f}%" if kelly_edge > 0 else f"{kelly_edge*100:.1f}%"
                kelly_str = f"{kelly_pct*100:.1f}%" if kelly_pct > 0 else "—"

                # 市场背离标记
                disagreement = abs(prob - implied)
                risk_flag = ""
                if kelly_pct > 0 and disagreement > HIGH_RISK_DISAGREEMENT:
                    risk_flag = "⚠️高风险"
                elif kelly_pct > 0:
                    risk_flag = "✅"

                icon = "✅ " if kelly_pct > 0 else ""
                lines.append(f"| {icon}{tip_label} | {fmt_prob(prob)} | {odds_val:.2f} | {fmt_prob(implied)} | {edge_str} | {kelly_str} | {risk_flag} |")
            lines.append("")

            # 价值标记
            if m["is_value"]:
                val_label = {"home_win": "主胜", "draw": "平局", "away_win": "客胜"}.get(
                    m.get("value_tip"), m.get("value_tip", "?"))
                risk_label = ""
                # 检查是否是高风险
                val_tip_key = m.get("value_tip")
                if val_tip_key:
                    val_prob = pred.get(val_tip_key, 0)
                    val_odds = m.get(f"odds_{val_tip_key}", 0)
                    if val_odds > 0:
                        val_implied = 1 / val_odds
                        if abs(val_prob - val_implied) > HIGH_RISK_DISAGREEMENT:
                            risk_label = " ⚠️ ⚠️ ⚠️ 高风险: 模型与市场显著背离，请谨慎参考"

                lines.append(f"> 🎯 **价值推荐**: {val_label} @ {m['value_odds']:.2f}{risk_label}")
                lines.append("")

            lines.append("")

    # ── 尾注 ──
    lines.append("---")
    lines.append("")
    lines.append("### 📡 数据源")
    key_masked = odds_key[:8] + "..." if len(odds_key) > 8 else odds_key
    lines.append(f"- 赔率: [The Odds API](https://the-odds-api.com) (Key: `{key_masked}`)")
    lines.append(f"- 赛果: [football-data.org](https://www.football-data.org)")
    lines.append("")
    lines.append("### 🛠 v2 优化内容")
    lines.append("- **Bayesian shrinkage**: 小样本攻防强度向联赛均值收缩，避免极端估值")
    lines.append("- **杯赛参数**: 国内杯赛场均进球×0.82，洲际杯赛×0.90")
    lines.append("- **中立场检测**: 中立场取消主场优势，主客场均用客场均值")
    lines.append("- **赛季+近期双轨**: 0.6赛季整体 + 0.4近10场加权")
    lines.append("- **市场背离预警**: 模型与赔率背离>25%时标记⚠️高风险")
    lines.append("")
    lines.append("> ⚠️ **免责声明**: 仅供研究和娱乐参考。历史数据不保证未来表现。")
    lines.append("> 模型未考虑伤病、转会、天气等因素。请理性决策，量力而行。")

    report = "\n".join(lines)
    print(report)

    # 统计到 stderr
    n_high_risk = sum(1 for p in value_picks if p["is_high_risk"])
    n_safe = len(value_picks) - n_high_risk
    print(f"\n📊 统计: {total_matches} 场比赛, {len(value_picks)} 个价值推荐 ({n_safe} 低风险, {n_high_risk} 高风险)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
