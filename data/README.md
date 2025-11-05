# 房價數據檔案說明

## 檔案位置

`data/taichung_prices.csv`

## 資料來源

**內政部實價登錄開放資料**

- 官方網站：https://plvr.land.moi.gov.tw/
- 開放資料平台：https://data.gov.tw/

## 如何下載真實資料

### 方法 1：從政府開放資料平台下載

1. 前往：https://data.gov.tw/
2. 搜尋：「不動產實價登錄」或「台中市」
3. 選擇資料集：「不動產買賣實價登錄批次資料」
4. 下載 CSV 格式檔案
5. 選擇台中市的資料
6. 將下載的 CSV 檔案重新命名為 `taichung_prices.csv`
7. 放置於 `data/` 目錄

### 方法 2：從內政部實價登錄網站下載

1. 前往：https://plvr.land.moi.gov.tw/
2. 選擇「批次下載」
3. 選擇「台中市」
4. 選擇時間範圍（建議下載近 5 年資料）
5. 下載 CSV 檔案
6. 解壓縮後放置於 `data/taichung_prices.csv`

## CSV 欄位說明

### 必要欄位

| 欄位名稱 | 說明 | 範例 |
|---------|------|------|
| **鄉鎮市區** | 行政區 | 北屯區 |
| **交易年月日** | 交易日期（民國年） | 1130515 |
| **土地位置建物門牌** | 完整地址 | 臺中市北屯區文心路四段 |
| **總價元** | 成交總價（元） | 8500000 |
| **建物移轉總面積平方公尺** | 建物面積（平方公尺） | 35.5 |
| **單價元平方公尺** | 單價（元/平方公尺） | 239436.62 |
| **土地移轉總面積平方公尺** | 土地面積（平方公尺） | 10.65 |
| **屋齡** | 房屋屋齡（年） | 5 |
| **建物型態** | 建築類型 | 住宅大樓(11層含以上有電梯) |
| **移轉層次** | 樓層 | 7/15 |

### 日期格式

- 民國年格式：`YYYMMDD`（例如：1130515 = 民國 113 年 5 月 15 日）
- 程式會自動轉換為西元年

### 面積單位轉換

- 平方公尺 → 坪：乘以 0.3025
- 程式會自動進行單位轉換

### 價格單位轉換

- 元 → 萬元：除以 10000
- 程式會自動進行單位轉換

## 範例數據

目前 `taichung_prices.csv` 包含 30 筆範例數據，涵蓋：
- 北屯區、西屯區、南屯區
- 近 2 年的交易記錄
- 各種建物型態（住宅大樓、華廈）

**實際生產環境請替換為真實的政府開放資料！**

## 資料更新頻率

- 政府開放資料每季更新
- 建議每季重新下載最新資料
- 或設定自動化腳本定期更新

## 注意事項

1. **編碼格式**：檔案必須為 UTF-8 編碼
2. **檔案大小**：真實資料可能有數百 MB，請確保有足夠空間
3. **效能考量**：首次讀取會較慢，後續查詢會使用快取
4. **快取時間**：預設 24 小時，可在 `.env` 中設定 `PRICE_CACHE_TTL_HOURS`

## 疑難排解

### 錯誤：找不到房價數據檔案

**原因：** CSV 檔案不存在

**解決方法：**
```bash
# 確認檔案存在
ls -lh data/taichung_prices.csv

# 如果不存在，從政府平台下載
```

### 錯誤：CSV 檔案缺少必要欄位

**原因：** 下載的 CSV 欄位名稱不符

**解決方法：**
1. 檢查 CSV 第一行（標題列）
2. 確認欄位名稱是否正確
3. 必要時手動修正欄位名稱

### 錯誤：CSV 檔案編碼錯誤

**原因：** 檔案編碼不是 UTF-8

**解決方法：**
```bash
# 檢查檔案編碼
file -i data/taichung_prices.csv

# 轉換為 UTF-8（如需要）
iconv -f BIG5 -t UTF-8 data/taichung_prices.csv -o data/taichung_prices_utf8.csv
mv data/taichung_prices_utf8.csv data/taichung_prices.csv
```

## 自動化更新腳本（可選）

可以設定定期下載最新資料的腳本：

```python
# scripts/update_price_data.py
import requests
import os

def download_latest_data():
    # 從政府平台下載最新資料
    url = "https://plvr.land.moi.gov.tw/..."  # 實際 URL
    response = requests.get(url)

    # 儲存檔案
    with open("data/taichung_prices.csv", "wb") as f:
        f.write(response.content)

    print("資料已更新")

if __name__ == "__main__":
    download_latest_data()
```

然後設定 crontab：
```bash
# 每月 1 號凌晨 3 點更新
0 3 1 * * cd /path/to/project && python3 scripts/update_price_data.py
```

## 聯絡資訊

如有問題，請聯繫：
- GitHub Issues: [專案連結]
- Email: [管理員信箱]
