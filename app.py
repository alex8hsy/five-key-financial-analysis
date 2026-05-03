"""
五大關鍵數字力財務分析系統
基於林明樟（MJ老師）財報分析理論
本系統僅提供財務數據的客觀呈現與分析，不構成任何投資建議。
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import yfinance as yf
import traceback
import re

app = Flask(__name__)
CORS(app)

# ============================================================
# 工具函數
# ============================================================

def py_val(v):
    """確保數值為 Python 原生型別"""
    try:
        if v is None: return 0.0
        return float(v)
    except: return 0.0

def safe_div(a, b):
    if py_val(b) == 0: return 0.0
    return round(py_val(a) / py_val(b), 4)

def get_val(df, key):
    """從 DataFrame 安全取值（取最新一列）"""
    try:
        if df is None or df.empty or key not in df.index:
            return 0.0
        return py_val(df.loc[key].iloc[0])
    except:
        return 0.0


def normalize_ticker(raw):
    """
    自動糾正常見的股票代碼輸入格式

    規則：
    - 已有市場後綴 → 直接使用（但修正 HK 5位數為 4 位）
    - 含股份類別的美股代碼 → 正規化（如 BRKA→BRK-A, BRK.A→BRK-A, BRK-B→BRK-B）
    - 純數字 5 位 → 港股（補齊 4 位）如 00700→0700.HK
    - 純數字 6 位 → A股：600-605 開頭→.SS，000-003/300-301 開頭→.SZ
    - 純數字 1-4 位且 0 開頭 → 港股（補齊 4 位）如 0700→0700.HK
    - 純數字 1-4 位非 0 開頭 → 優先嘗試台股，再嘗試港股
    - 英文無後綴 → 美股
    """
    t = raw.strip().upper()

    # 處理已有市場後綴
    for suffix in ['.HK', '.SS', '.SZ', '.TW', '.TWO', '.T', '.L', '.SI', '.KS']:
        if t.endswith(suffix):
            if suffix == '.HK':
                code = t[:-3]
                if code.isdigit() and len(code) > 4:
                    t = f'{code.lstrip("0").zfill(4)}.HK'
            return t

    # 非純數字 → 美股代碼處理
    if not t.isdigit():
        # 處理含股份類別的美股代碼
        # 常見格式：BRKA / BRKB / BRK.A / BRK.B / BRK-A / BRK-B
        # Yahoo Finance 使用連字符格式：BRK-A, BRK-B
        m = re.match(r'^([A-Z]+)\.([A-Z])$', t)
        if m:
            # BRK.A → BRK-A
            return f'{m.group(1)}-{m.group(2)}'
        m = re.match(r'^([A-Z]+)-([A-Z])$', t)
        if m:
            # BRK-A 已經是正確格式
            return t
        m = re.match(r'^([A-Z]{2,})([A-Z])$', t)
        if m:
            # BRKA → 嘗試 BRK-A（拆分最後一個字母）
            base, cls = m.group(1), m.group(2)
            candidate = f'{base}-{cls}'
            try:
                test = yf.Ticker(candidate)
                name = test.info.get('longName') or test.info.get('shortName') or ''
                if name and name != candidate and len(name) > 3:
                    return candidate
            except:
                pass
        return t

    # --- 純數字，按位數推測 ---
    digit_len = len(t)

    # 5 位數 → 港股（去掉前導零，補齊 4 位）
    if digit_len == 5:
        return f'{t.lstrip("0").zfill(4)}.HK'

    # 6 位數 → A股（保留原始開頭判斷）
    if digit_len == 6:
        if t.startswith(('600', '601', '603', '605')):
            return f'{t}.SS'
        elif t.startswith(('000', '001', '002', '003', '300', '301')):
            return f'{t}.SZ'
        else:
            return f'{t}.SS'

    # 1-4 位數 → 根據首位數字判斷優先順序
    hk_try = t.zfill(4)
    hk_code = f'{hk_try}.HK'
    tw_code = f'{t}.TW'
    two_code = f'{t}.TWO'

    # 若補齊後以 0 開頭（如 0700），優先嘗試港股
    # 若不以 0 開頭（如 2330），優先嘗試台股
    if hk_try.startswith('0'):
        # 港股優先
        try:
            test = yf.Ticker(hk_code)
            name = test.info.get('longName') or test.info.get('shortName') or ''
            if name and name != hk_code and len(name) > 3:
                return hk_code
        except:
            pass
        try:
            test = yf.Ticker(tw_code)
            name = test.info.get('longName') or test.info.get('shortName') or ''
            if name and name != tw_code and len(name) > 3:
                return tw_code
        except:
            pass
        try:
            test = yf.Ticker(two_code)
            name = test.info.get('longName') or test.info.get('shortName') or ''
            if name and name != two_code and len(name) > 3:
                return two_code
        except:
            pass
        return hk_code
    else:
        # 台股優先（如 2330 → 台積電）
        try:
            test = yf.Ticker(tw_code)
            name = test.info.get('longName') or test.info.get('shortName') or ''
            if name and name != tw_code and len(name) > 3:
                return tw_code
        except:
            pass
        try:
            test = yf.Ticker(two_code)
            name = test.info.get('longName') or test.info.get('shortName') or ''
            if name and name != two_code and len(name) > 3:
                return two_code
        except:
            pass
        try:
            test = yf.Ticker(hk_code)
            name = test.info.get('longName') or test.info.get('shortName') or ''
            if name and name != hk_code and len(name) > 3:
                return hk_code
        except:
            pass
        return tw_code


# ============================================================
# 五大數字力分析引擎
# ============================================================

def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        bs = stock.balance_sheet
        inc = stock.financials
        cf = stock.cashflow

        # --- 數據提取 (從 info + 報表) ---
        company_name = info.get('longName') or info.get('shortName') or ticker
        sector = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')
        market_cap = py_val(info.get('marketCap'))
        price = py_val(info.get('currentPrice') or info.get('regularMarketPrice'))
        currency = info.get('currency', 'USD')

        # 資產負債表
        total_assets = get_val(bs, 'Total Assets')
        current_assets = get_val(bs, 'Current Assets')
        current_liabilities = get_val(bs, 'Current Liabilities')
        total_liabilities = get_val(bs, 'Total Liabilities Net Minority Interest')
        equity = get_val(bs, 'Stockholders Equity')
        cash_equiv = get_val(bs, 'Cash Cash Equivalents And Short Term Investments')
        inventory = get_val(bs, 'Inventory')
        receivables = get_val(bs, 'Receivables')
        accounts_receivable = get_val(bs, 'Accounts Receivable')
        total_debt = get_val(bs, 'Total Debt')

        # 損益表
        revenue = get_val(inc, 'Total Revenue')
        cogs = get_val(inc, 'Cost Of Revenue')
        gross_profit = get_val(inc, 'Gross Profit')
        operating_income = get_val(inc, 'Operating Income')
        net_income = get_val(inc, 'Net Income Common Stockholders')

        # 現金流量表
        ocf = get_val(cf, 'Operating Cash Flow')
        capex = abs(get_val(cf, 'Capital Expenditure'))
        fcf = get_val(cf, 'Free Cash Flow')

        # info 中的輔助數據
        ebitda = py_val(info.get('ebitda'))
        interest_expense = py_val(info.get('interestExpense'))
        gross_margin_info = py_val(info.get('grossMargins')) * 100
        ebitda_margin = py_val(info.get('ebitdaMargins')) * 100

        # ==============================================
        # A：現金流量 —「比氣長，越長越好」
        # ==============================================
        cf_ratio = safe_div(ocf, current_liabilities) * 100
        cash_to_assets = safe_div(cash_equiv, total_assets) * 100

        # 5 年現金流量允當比率
        cf_adequacy = 0.0
        if not cf.empty:
            ocf_5y = sum(py_val(cf.loc['Operating Cash Flow'].iloc[i]) for i in range(min(5, len(cf.columns))))
            capex_5y = abs(sum(py_val(cf.loc['Capital Expenditure'].iloc[i]) for i in range(min(5, len(cf.columns)))))
            cf_adequacy = safe_div(ocf_5y, capex_5y) * 100 if capex_5y > 0 else 0.0

        # 現金再投資比率
        reinvest_denom = total_assets - current_liabilities
        cf_reinvest = safe_div(fcf, reinvest_denom) * 100 if reinvest_denom > 0 else 0.0

        rule_pass = {
            'cf_ratio': cf_ratio > 100,
            'cf_adequacy': cf_adequacy > 100,
            'cf_reinvest': cf_reinvest > 10,
        }
        rule_score = sum(rule_pass.values())

        cf_score = min(100, int(
            min(35, cf_ratio / 100 * 15) +
            min(30, cf_adequacy / 100 * 10) +
            min(15, cf_reinvest / 10 * 10) +
            min(20, cash_to_assets / 25 * 20)
        ))

        cash_flow = dim_result('現金流量', '比氣長，越長越好', cf_score, {
            '現金流量比率': (cf_ratio, '%', '>100%', cf_ratio > 100),
            '現金流量允當比率': (cf_adequacy, '%', '>100%', cf_adequacy > 100),
            '現金再投資比率': (cf_reinvest, '%', '>10%', cf_reinvest > 10),
            '現金佔總資產比率': (cash_to_assets, '%', '10%-25%', 10 <= cash_to_assets <= 60),
        }, cf_insight(cf_ratio, cf_adequacy, cf_reinvest, cash_to_assets), rule_score, rule_pass)

        # ==============================================
        # B：經營能力 —「翻桌率，越高越好」
        # ==============================================
        ar_turnover = safe_div(revenue, accounts_receivable)
        avg_days = safe_div(365, ar_turnover) if ar_turnover > 0 else 365.0
        inv_turnover = safe_div(cogs, inventory)
        ta_turnover = safe_div(revenue, total_assets)

        op_score = min(100, int(
            min(30, ar_turnover / 12 * 30) +
            min(25, max(0, (90 - avg_days) / 90 * 25)) +
            min(25, inv_turnover / 6 * 25) +
            min(20, ta_turnover / 2 * 20)
        ))

        operating = dim_result('經營能力', '翻桌率，越高越好', op_score, {
            '應收帳款週轉率': (ar_turnover, '次/年', '>6次', ar_turnover > 6),
            '平均收現日數': (avg_days, '天', '<90天', avg_days < 90),
            '存貨週轉率': (inv_turnover, '次/年', '>2次', inv_turnover > 2),
            '總資產週轉率': (ta_turnover, '次/年', '>1次', ta_turnover > 1),
        }, op_insight(ar_turnover, avg_days, inv_turnover, ta_turnover))

        # ==============================================
        # C：獲利能力 —「這是不是一門好生意？」
        # ==============================================
        gm = safe_div(gross_profit, revenue) * 100
        om = safe_div(operating_income, revenue) * 100
        nm = safe_div(net_income, revenue) * 100
        roe = safe_div(net_income, equity) * 100

        if gm < 1 and gross_margin_info > 0: gm = gross_margin_info

        profit_score = min(100, int(
            min(45, gm / 50 * 45) +
            min(25, om / 30 * 25) +
            min(15, nm / 20 * 15) +
            min(15, roe / 20 * 15)
        ))

        profitability = dim_result('獲利能力', '這是不是一門好生意？', profit_score, {
            '毛利率': (gm, '%', '>30%', gm > 30),
            '營業利益率': (om, '%', '>10%', om > 10),
            '淨利率': (nm, '%', '>10%', nm > 10),
            '股東權益報酬率(ROE)': (roe, '%', '>15%', roe > 15),
        }, profit_insight(gm, om, nm, roe))

        # ==============================================
        # D：財務結構 —「那一根棒子」
        # ==============================================
        debt_ratio = safe_div(total_liabilities, total_assets) * 100
        eq_ratio = safe_div(equity, total_assets) * 100
        dte = safe_div(total_debt, equity) * 100

        if debt_ratio < 30: struct_score = 92
        elif debt_ratio < 50: struct_score = 78
        elif debt_ratio < 60: struct_score = 55
        elif debt_ratio < 70: struct_score = 35
        else: struct_score = 15

        financial_structure = dim_result('財務結構', '那一根棒子', struct_score, {
            '負債佔總資產比率': (debt_ratio, '%', '<50%', debt_ratio < 50),
            '股東權益佔總資產比率': (eq_ratio, '%', '>50%', eq_ratio > 50),
        }, struct_insight(debt_ratio, dte))

        # ==============================================
        # E：償債能力 —「您欠我的，能還嗎？」
        # ==============================================
        cur_ratio = safe_div(current_assets, current_liabilities) * 100
        q_ratio = safe_div(current_assets - inventory, current_liabilities) * 100
        if q_ratio <= 0: q_ratio = cur_ratio * 0.8
        int_cov = safe_div(ebitda, interest_expense)

        debt_score = min(100, int(
            min(40, cur_ratio / 300 * 40) +
            min(35, q_ratio / 200 * 35) +
            min(25, int_cov / 10 * 25)
        ))

        debt_ability = dim_result('償債能力', '您欠我的，能還嗎？', debt_score, {
            '流動比率': (cur_ratio, '%', '>200%', cur_ratio > 200),
            '速動比率': (q_ratio, '%', '>100%', q_ratio > 100),
            '利息保障倍數': (int_cov, '倍', '>5倍', int_cov > 5),
        }, debt_insight(cur_ratio, q_ratio, int_cov))

        # ==============================================
        # 綜合總評
        # ==============================================
        dims = [cash_flow, operating, profitability, financial_structure, debt_ability]
        total_score = int(
            cf_score * 0.25 + op_score * 0.25 + profit_score * 0.20 +
            struct_score * 0.15 + debt_score * 0.15
        )
        overall_grade, overall_advice = overall_eval(total_score, dims)

        # 判斷市場
        ticker_upper = ticker.upper()
        if '.TW' in ticker_upper or '.TWO' in ticker_upper:
            market = '台股'
        elif '.HK' in ticker_upper:
            market = '港股'
        elif '.SS' in ticker_upper or '.SZ' in ticker_upper:
            market = 'A股'
        else:
            market = '美股'

        return {
            'success': True,
            'ticker': ticker_upper,
            'company_name': company_name,
            'sector': sector, 'industry': industry,
            'market': market,
            'market_cap': market_cap, 'current_price': price, 'currency': currency,
            'total_score': total_score,
            'overall_grade': overall_grade,
            'overall_advice': overall_advice,
            'dimensions': dims,
            'spark_data': {
                'gross_margin': gm, 'operating_margin': om, 'net_margin': nm, 'roe': roe,
                'debt_ratio': debt_ratio, 'current_ratio': cur_ratio, 'quick_ratio': q_ratio,
                'cash_to_assets': cash_to_assets, 'ar_turnover': ar_turnover,
                'inventory_turnover': inv_turnover, 'total_asset_turnover': ta_turnover,
                'avg_collection_days': avg_days,
            }
        }

    except Exception as e:
        traceback.print_exc()
        return {'success': False, 'ticker': ticker, 'error': str(e)}


# ============================================================
# 輔助函數
# ============================================================

def dim_result(label, cn, score, metrics, insight, rule_s=None, rule_d=None):
    d = {
        'label': label, 'zhongfanzhong': cn, 'score': int(score),
        'grade': grade(score),
        'metrics': {k: {'value': round(v[0], 1), 'unit': v[1], 'threshold': v[2], 'pass': v[3]} for k, v in metrics.items()},
        'insight': insight,
    }
    if rule_s is not None:
        d['rule_100'] = rule_s
        d['rule_100_detail'] = rule_d
    return d


def grade(score):
    if score >= 80: return {'level': 'A', 'color': '#10b981', 'text': '表現優異'}
    elif score >= 60: return {'level': 'B', 'color': '#f59e0b', 'text': '表現良好'}
    elif score >= 40: return {'level': 'C', 'color': '#f97316', 'text': '表現一般'}
    return {'level': 'D', 'color': '#ef4444', 'text': '待觀察'}


def cf_insight(r, a, re, cp):
    """現金流量維度洞察 — 僅客觀描述數據，不提供投資建議"""
    parts = []
    if r > 100: parts.append('📊 現金流量比率 >100%，營運現金充足')
    elif r > 50: parts.append('📊 現金流量比率介於 50%-100% 之間')
    else: parts.append('📊 現金流量比率低於 50%')
    if a > 100: parts.append('📊 五年現金流量允當比率 >100%')
    if re > 10: parts.append('📊 現金再投資比率 >10%')
    if cp >= 10: parts.append(f'📊 現金佔總資產 {cp:.1f}%')
    elif cp > 0: parts.append(f'📊 現金佔總資產 {cp:.1f}%')
    return ' | '.join(parts) if parts else '數據尚在整理中'


def op_insight(ar, days, inv, ta):
    """經營能力維度洞察 — 僅客觀描述數據，不提供投資建議"""
    parts = []
    if ar > 6: parts.append(f'📊 應收帳款週轉 {ar:.1f} 次/年')
    if days < 90: parts.append(f'📊 收現天數 {days:.0f} 天')
    elif days < 180: parts.append(f'📊 收現天數 {days:.0f} 天')
    else: parts.append(f'📊 收現天數 {days:.0f} 天，回款週期較長')
    if inv > 2: parts.append(f'📊 存貨週轉 {inv:.1f} 次/年')
    if ta > 1: parts.append(f'📊 總資產週轉率 {ta:.2f}')
    return ' | '.join(parts) if parts else '數據尚在整理中'


def profit_insight(gm, om, nm, roe):
    """獲利能力維度洞察 — 僅客觀描述數據，不提供投資建議"""
    parts = []
    if gm > 50: parts.append(f'📊 毛利率 {gm:.1f}%，利潤空間寬裕')
    elif gm > 30: parts.append(f'📊 毛利率 {gm:.1f}%，具備一定競爭力')
    elif gm > 10: parts.append(f'📊 毛利率 {gm:.1f}%，利潤空間偏小')
    else: parts.append(f'📊 毛利率 {gm:.1f}%')
    if om > 10: parts.append(f'📊 營業利益率 {om:.1f}%，本業獲利穩健')
    if roe > 15: parts.append(f'📊 ROE {roe:.1f}%')
    return ' | '.join(parts) if parts else '數據尚在整理中'


def struct_insight(dr, dte):
    """財務結構維度洞察 — 僅客觀描述數據，不提供投資建議"""
    if dr < 30: return f'📊 負債比 {dr:.1f}%，財務結構穩健'
    elif dr < 50: return f'📊 負債比 {dr:.1f}%，結構健康'
    elif dr < 60: return f'📊 負債比 {dr:.1f}%，持續觀察中'
    return f'📊 負債比 {dr:.1f}%，負債趨勢需留意'


def debt_insight(cr, qr, ic):
    """償債能力維度洞察 — 僅客觀描述數據，不提供投資建議"""
    parts = []
    if cr > 200: parts.append(f'📊 流動比率 {cr:.1f}%')
    elif cr > 100: parts.append(f'📊 流動比率 {cr:.1f}%')
    else: parts.append(f'📊 流動比率 {cr:.1f}%')
    if qr > 100: parts.append('📊 速動比率 >100%')
    if ic > 5: parts.append(f'📊 利息保障 {ic:.1f} 倍')
    return ' | '.join(parts) if parts else '數據尚在整理中'


def overall_eval(total, dims):
    """綜合總評 — 僅客觀描述財務體質，不提供投資建議"""
    scores = [d['score'] for d in dims]
    weak = sum(1 for s in scores if s < 40)
    if total >= 80 and weak == 0:
        return {'level': 'A', 'color': '#10b981', 'text': '表現優異'}, '📊 五大數字力全面達標，財務體質穩健。'
    elif total >= 65 and weak <= 1:
        return {'level': 'B', 'color': '#3b82f6', 'text': '表現良好'}, '📊 整體財務體質良好，部分維度有提升空間。'
    elif total >= 45:
        return {'level': 'C', 'color': '#f59e0b', 'text': '表現一般'}, '📊 部分指標偏弱，需進一步了解原因。'
    else:
        return {'level': 'D', 'color': '#ef4444', 'text': '待觀察'}, '📊 多項指標表現偏弱，需持續追蹤觀察。'


# ============================================================
# Routes
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze')
def analyze():
    ticker = request.args.get('ticker', '').strip()
    if not ticker:
        return jsonify({'success': False, 'error': '請輸入股票代碼'})
    ticker = normalize_ticker(ticker)
    return jsonify(analyze_stock(ticker))

@app.route('/api/quick/<ticker>')
def quick(ticker):
    ticker = normalize_ticker(ticker.strip())
    return jsonify(analyze_stock(ticker))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
