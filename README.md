# 五大關鍵數字力財務分析系統

基於林明樟（MJ老師）《不懂財報，也能輕鬆選出賺錢績優股》理論的財務分析儀表板。

## 功能特色

- **五大數字力分析**：現金流量、經營能力、獲利能力、財務結構、償債能力
- **多市場支援**：美股、港股、中國 A 股、台股
- **智慧代碼識別**：自動辨識市場並轉換格式
- **雷達圖視覺化**：Chart.js 五維雷達圖 + 關鍵指標條形圖
- **客觀數據呈現**：僅提供財務數據分析，不構成投資建議

## 支援的輸入格式

| 市場 | 輸入範例 | 自動轉換 |
|------|---------|---------|
| 美股 | `AAPL` `NVDA` `BRKA` `BRK.A` | 直接使用 / `BRKA`→`BRK-A` |
| 港股 | `00700` `0700` `0700.HK` | → `0700.HK` |
| A 股 | `600519` `000858` `600519.SS` | → `600519.SS` / `000858.SZ` |
| 台股 | `2330` `2454` `2330.TW` | → `2330.TW` |

## 快速開始

### 環境需求

- Python 3.8+
- pip

### 安裝與運行

```bash
# 克隆倉庫
git clone https://github.com/<your-username>/five-key-financial-analysis.git
cd five-key-financial-analysis

# 安裝依賴
pip install -r requirements.txt

# 啟動服務
python app.py
```

服務啟動後，在瀏覽器中打開 `http://localhost:5050`。

## 分析維度說明

| 維度 | 核心概念 | 關鍵指標 |
|------|---------|---------|
| A. 現金流量 | 比氣長，越長越好 | 現金流量比率、允當比率、再投資比率 |
| B. 經營能力 | 翻桌率，越高越好 | 應收帳款週轉率、存貨週轉率、總資產週轉率 |
| C. 獲利能力 | 這是不是一門好生意？ | 毛利率、營業利益率、淨利率、ROE |
| D. 財務結構 | 那一根棒子 | 負債比、股東權益比 |
| E. 償債能力 | 您欠我的，能還嗎？ | 流動比率、速動比率、利息保障倍數 |

## 部署到 Render（免費上線）

本項目已配置好 Render 部署文件（`render.yaml` + `Procfile`），可直接一鍵部署。

### 步驟

1. **登入 Render**：打開 [https://dashboard.render.com](https://dashboard.render.com)，使用 GitHub 帳號登入
2. **新建 Blueprint**：點擊 **New** → 選擇 **Blueprint**
3. **連接倉庫**：選擇 `five-key-financial-analysis` 倉庫，點擊 **Connect**
4. **確認配置**：Render 會自動識別以下配置，無需手動修改
   - **Runtime**：Python
   - **Build Command**：`pip install -r requirements.txt`
   - **Start Command**：`gunicorn app:app`
   - **Instance Type**：選 **Free**（免費套餐）
5. **開始部署**：點擊 **Apply**，等待約 2-3 分鐘
6. **訪問網站**：部署完成後，Render 會分配一個公網地址，格式如：
   `https://five-key-financial-analysis-xxxx.onrender.com`

### 注意事項

- 免費套餐會在 **15 分鐘無流量後自動休眠**，再次訪問時需等待約 30 秒冷啟動
- 如需自定義域名，可在 Render 服務的 **Settings** 中配置
- 如需更新代碼，推送到 GitHub `main` 分支後，Render 會自動重新部署

## 技術架構

- **後端**：Flask + Gunicorn + yfinance（財務數據來源：Yahoo Finance）
- **前端**：原生 HTML/CSS/JS + Chart.js（雷達圖）
- **數據來源**：Yahoo Finance 公開資訊
- **部署**：Render（免費）/ Gunicorn 生產伺服器

## 免責聲明

本工具僅基於公開財務數據進行客觀分析，不構成任何投資建議、投資推薦或買賣指示。所有投資決策及風險由使用者自行承擔。

## 授權

MIT License
