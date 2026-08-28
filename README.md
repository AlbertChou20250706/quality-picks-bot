# quality-picks-bot

每月自動篩選台股／美股的優質個股與 ETF，透過 GitHub Actions 排程執行，經 LINE Messaging API 推播。

## 做什麼

- 從候選池（`config/candidates_*.json`，各市場、各類別 6～8 檔）抓取真實基本面／ETF 資料（yfinance）
- 依量化公式排序，選出台股個股／台股 ETF／美股個股／美股 ETF 各前 3 名（`src/screen_and_rank.py`）
- 呼叫 Claude 針對已經排好序的前 3 名撰寫入選理由（只能引用程式算好的數字，不能重新排序或編數字）
- 組成 LINE Flex Message 卡片並推播

## 跟其他兩個自動化的差異

- `ai-stock-weekly-report-bot`／`stock-committee-bot` 看的是**價格動能**（週漲跌、RS 動能），這個 repo 看的是**基本面品質**（ROE、毛利率、自由現金流、ETF 費用率／規模），資料變化緩慢，所以排程是**每月一次**，不是每週或每日。
- 候選池是固定的一組知名龍頭／ETF，不是全市場掃描（免費 API＋GitHub Actions 排程的架構下，全市場逐檔查詢不現實）。

## 篩選邏輯

**個股**：0.35×ROE + 0.25×營益率(或毛利率) + 0.20×自由現金流為正 + 0.20×股利品質，每項先在候選池內做 min-max 標準化，缺資料的欄位得分視為 0（不用平均值猜測，避免獎勵到缺資料的標的）。

**ETF**：0.5×資產規模 + 0.5×(1 − 費用率)，同樣先標準化。

不做共同基金（Sharpe／Alpha／最大回撤／4433 排名缺乏已驗證的免費資料源，暫不涵蓋）。

## 環境變數 / GitHub Secrets

- `ANTHROPIC_API_KEY`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_PUSH_TARGET_IDS`（逗號分隔多個 user/group id）

## 免責聲明

每次輸出固定附上：「投資一定有風險，基金/ETF/股票投資有賺有賠，以上資訊非投資建議」，由程式碼強制附加，不依賴模型輸出。
