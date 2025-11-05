"""房價查詢服務 - 整合內政部實價登錄 API."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import hashlib


logger = logging.getLogger(__name__)


# ==================== 數據類定義 ====================

@dataclass
class Transaction:
    """單筆交易記錄."""
    district: str  # 區域（例如：北屯區）
    road: str  # 路名
    price: float  # 總價（萬元）
    unit_price: float  # 單價（萬/坪）
    building_area: float  # 建物面積（坪）
    land_area: float  # 土地面積（坪）
    building_age: Optional[int]  # 屋齡（年）
    transaction_date: str  # 交易年月（例如：11201）
    building_type: str  # 建物型態
    floor: Optional[str]  # 樓層


@dataclass
class ProjectGroup:
    """建案分組（同路段、門牌相近）."""
    road_name: str  # 路段名稱（例如：文心路）
    address_range: str  # 門牌範圍（例如：100-120號）
    min_number: int  # 最小門牌號
    max_number: int  # 最大門牌號
    transaction_count: int  # 成交筆數
    avg_price: float  # 平均總價（萬元）
    avg_unit_price: float  # 平均單價（萬/坪）
    addresses: List[str]  # 成交門牌列表（例如：['#100', '#105', '#110']）
    transactions: List[Transaction]  # 該組的所有交易記錄


@dataclass
class PriceStatistics:
    """價格統計資料."""
    area: str  # 查詢地區
    total_transactions: int  # 總交易筆數
    avg_price: float  # 平均總價（萬元）
    avg_unit_price: float  # 平均單價（萬/坪）
    max_price: float  # 最高總價（萬元）
    min_price: float  # 最低總價（萬元）
    max_unit_price: float  # 最高單價（萬/坪）
    min_unit_price: float  # 最低單價（萬/坪）
    median_age: Optional[float]  # 屋齡中位數
    price_trend: Dict[str, float]  # 價格趨勢（年月 -> 平均單價）
    query_period: str  # 查詢期間
    project_groups: List[ProjectGroup]  # 建案分組（新增）


# ==================== 快取機制 ====================

class PriceCache:
    """房價查詢快取."""

    def __init__(self, ttl_hours: int = 24):
        self._cache: Dict[str, Tuple[PriceStatistics, datetime]] = {}
        self._ttl = timedelta(hours=ttl_hours)

    def _make_key(self, area: str) -> str:
        """生成快取鍵."""
        normalized = area.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, area: str) -> Optional[PriceStatistics]:
        """獲取快取數據."""
        key = self._make_key(area)
        if key in self._cache:
            stats, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                logger.info(f"快取命中 | area={area}")
                return stats
            else:
                logger.info(f"快取過期 | area={area}")
                del self._cache[key]
        return None

    def set(self, area: str, stats: PriceStatistics) -> None:
        """設置快取數據."""
        key = self._make_key(area)
        self._cache[key] = (stats, datetime.now())
        logger.info(f"快取已更新 | area={area}")

    def clear(self) -> None:
        """清空快取."""
        self._cache.clear()
        logger.info("快取已清空")


# 全域快取實例
_price_cache = PriceCache()


# ==================== 地區名稱處理 ====================

# 台中市行政區對照表
TAICHUNG_DISTRICTS = {
    "中區": "中區",
    "東區": "東區",
    "西區": "西區",
    "南區": "南區",
    "北區": "北區",
    "西屯": "西屯區",
    "西屯區": "西屯區",
    "南屯": "南屯區",
    "南屯區": "南屯區",
    "北屯": "北屯區",
    "北屯區": "北屯區",
    "豐原": "豐原區",
    "豐原區": "豐原區",
    "東勢": "東勢區",
    "東勢區": "東勢區",
    "大甲": "大甲區",
    "大甲區": "大甲區",
    "清水": "清水區",
    "清水區": "清水區",
    "沙鹿": "沙鹿區",
    "沙鹿區": "沙鹿區",
    "梧棲": "梧棲區",
    "梧棲區": "梧棲區",
    "后里": "后里區",
    "后里區": "后里區",
    "神岡": "神岡區",
    "神岡區": "神岡區",
    "潭子": "潭子區",
    "潭子區": "潭子區",
    "大雅": "大雅區",
    "大雅區": "大雅區",
    "新社": "新社區",
    "新社區": "新社區",
    "石岡": "石岡區",
    "石岡區": "石岡區",
    "外埔": "外埔區",
    "外埔區": "外埔區",
    "大安": "大安區",
    "大安區": "大安區",
    "烏日": "烏日區",
    "烏日區": "烏日區",
    "大肚": "大肚區",
    "大肚區": "大肚區",
    "龍井": "龍井區",
    "龍井區": "龍井區",
    "霧峰": "霧峰區",
    "霧峰區": "霧峰區",
    "太平": "太平區",
    "太平區": "太平區",
    "大里": "大里區",
    "大里區": "大里區",
    "和平": "和平區",
    "和平區": "和平區",
}


def normalize_area(area: str) -> Tuple[Optional[str], Optional[str]]:
    """
    正規化查詢地區名稱。

    Args:
        area: 用戶輸入的地區（例如：北屯、北屯區民族路、台中市西屯區）

    Returns:
        (district, road): 區域名稱和路名（可能為 None）

    Examples:
        "北屯" -> ("北屯區", None)
        "西屯區文心路" -> ("西屯區", "文心路")
        "台中市南屯區" -> ("南屯區", None)
    """
    # 移除「台中市」前綴
    area = area.replace("台中市", "").strip()

    # 嘗試匹配行政區
    district = None
    road = None

    for key, value in TAICHUNG_DISTRICTS.items():
        if area.startswith(key):
            district = value
            # 提取路名（移除行政區名稱後的部分）
            remaining = area[len(key):].strip()
            if remaining:
                road = remaining
            break

    return district, road


def suggest_similar_areas(query: str) -> List[str]:
    """建議相似的地區名稱."""
    query = query.lower().replace("區", "")
    suggestions = []

    for district in set(TAICHUNG_DISTRICTS.values()):
        district_base = district.replace("區", "").lower()
        if query in district_base or district_base in query:
            suggestions.append(district)

    return suggestions[:5]  # 最多返回 5 個建議


# ==================== CSV 數據快取 ====================

class CSVDataCache:
    """CSV 數據快取管理器."""

    def __init__(self):
        self._data: Optional[List[Dict[str, str]]] = None
        self._last_loaded: Optional[datetime] = None
        self._ttl = timedelta(hours=24)

    def is_valid(self) -> bool:
        """檢查快取是否有效."""
        if self._data is None or self._last_loaded is None:
            return False
        return datetime.now() - self._last_loaded < self._ttl

    def get(self) -> Optional[List[Dict[str, str]]]:
        """獲取快取數據."""
        if self.is_valid():
            logger.info("CSV 快取命中")
            return self._data
        return None

    def set(self, data: List[Dict[str, str]]) -> None:
        """設置快取數據."""
        self._data = data
        self._last_loaded = datetime.now()
        logger.info(f"CSV 快取已更新 | 筆數={len(data)}")

    def clear(self) -> None:
        """清空快取."""
        self._data = None
        self._last_loaded = None
        logger.info("CSV 快取已清空")


# 全域 CSV 快取實例
_csv_cache = CSVDataCache()


# ==================== CSV 數據讀取 ====================

async def load_csv_data(csv_path: str = "data/taichung_prices.csv", auto_download: bool = True) -> List[Dict[str, str]]:
    """
    讀取 CSV 檔案（帶快取和自動下載）。

    Args:
        csv_path: CSV 檔案路徑
        auto_download: 是否自動下載最新資料（預設為 True）

    Returns:
        CSV 數據列表（字典格式）

    Raises:
        FileNotFoundError: CSV 檔案不存在且下載失敗
        ValueError: CSV 格式錯誤
    """
    import csv
    import os
    from pathlib import Path

    # 檢查快取
    cached_data = _csv_cache.get()
    if cached_data:
        return cached_data

    # 自動下載最新資料（如果啟用）
    if auto_download:
        try:
            from . import data_downloader
            logger.info("正在檢查資料更新...")
            downloaded_path = await data_downloader.ensure_taichung_data()
            if downloaded_path:
                csv_path = str(downloaded_path)
                logger.info(f"✅ 資料檔案已就緒 | path={csv_path}")
        except Exception as e:
            logger.warning(f"⚠️ 自動下載失敗，將使用本地檔案 | error={e}")

    # 檢查檔案是否存在
    csv_file = Path(csv_path)
    if not csv_file.exists():
        logger.error(f"CSV 檔案不存在 | path={csv_path}")
        raise FileNotFoundError(
            f"找不到房價數據檔案：{csv_path}\n"
            f"請確認檔案路徑是否正確，或從政府開放資料平台下載最新資料。"
        )

    # 讀取 CSV 檔案
    try:
        logger.info(f"正在讀取 CSV 檔案 | path={csv_path}")

        # 使用 asyncio 避免阻塞
        await asyncio.sleep(0)  # 讓出控制權

        data = []
        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            # 清理欄位名稱，移除 BOM 和多餘空白
            if reader.fieldnames:
                reader.fieldnames = [
                    field.replace('\ufeff', '').strip() if field else field
                    for field in reader.fieldnames
                ]

            # 驗證必要欄位
            required_fields = ["鄉鎮市區", "交易年月日", "總價元", "建物移轉總面積平方公尺", "單價元平方公尺"]
            if not all(field in reader.fieldnames for field in required_fields):
                missing = [f for f in required_fields if f not in reader.fieldnames]
                logger.error(f"CSV 欄位名稱：{reader.fieldnames}")
                raise ValueError(f"CSV 檔案缺少必要欄位：{', '.join(missing)}")

            # 讀取所有資料
            for row in reader:
                data.append(row)

        logger.info(f"CSV 讀取完成 | 總筆數={len(data)}")

        # 列印所有不重複的地區名稱（用於除錯）
        districts = set()
        for row in data:
            district = row.get("鄉鎮市區", "").strip()
            if district:
                districts.add(district)

        logger.info(f"CSV 中的地區清單：{', '.join(sorted(districts))}")

        # 儲存到快取
        _csv_cache.set(data)

        return data

    except UnicodeDecodeError as exc:
        logger.error(f"CSV 檔案編碼錯誤 | path={csv_path} | error={exc}")
        raise ValueError(f"CSV 檔案編碼錯誤，請確認檔案為 UTF-8 編碼")
    except csv.Error as exc:
        logger.error(f"CSV 格式錯誤 | path={csv_path} | error={exc}")
        raise ValueError(f"CSV 檔案格式錯誤：{exc}")
    except Exception as exc:
        logger.error(f"讀取 CSV 失敗 | path={csv_path} | error={exc}")
        raise


# ==================== 數據過濾和轉換 ====================

def filter_by_district_and_road(
    data: List[Dict[str, str]],
    district: str,
    road: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    按地區和路名過濾數據（支援模糊匹配）。

    Args:
        data: CSV 數據列表
        district: 行政區（例如：北屯、北屯區、台中市北屯區）
        road: 路名（可選）

    Returns:
        過濾後的數據列表
    """
    filtered = []

    # 正規化查詢地區（移除「台中市」、「區」等）
    normalized_query = district.replace("台中市", "").replace("臺中市", "").strip()

    logger.debug(f"地區過濾 | 原始查詢={district} | 正規化={normalized_query}")

    for row in data:
        # 檢查行政區（模糊匹配）
        row_district = row.get("鄉鎮市區", "").strip()

        # 移除空白和特殊字符，進行模糊匹配
        if not row_district:
            continue

        # 方法 1：直接包含關係
        match = (
            normalized_query in row_district or
            row_district in normalized_query or
            # 方法 2：移除「區」後再比較
            normalized_query.replace("區", "") in row_district or
            row_district.replace("區", "") in normalized_query
        )

        if not match:
            continue

        # 檢查路名（如果有指定）
        if road:
            row_road = row.get("土地位置建物門牌", "")
            if road not in row_road:
                continue

        filtered.append(row)

    logger.debug(f"地區過濾結果 | 查詢={district} | 符合筆數={len(filtered)}")

    return filtered


def filter_by_date_range(
    data: List[Dict[str, str]],
    years: int = 5
) -> List[Dict[str, str]]:
    """
    按時間範圍過濾數據（過去 N 年）。

    Args:
        data: CSV 數據列表
        years: 年數（預設 5 年）

    Returns:
        過濾後的數據列表
    """
    from datetime import datetime, timedelta

    # 計算截止日期（N 年前）
    cutoff_date = datetime.now() - timedelta(days=years * 365)

    filtered = []

    for row in data:
        try:
            # 解析交易日期
            date_str = row.get("交易年月日", "")
            if not date_str:
                continue

            # 嘗試多種日期格式
            date_obj = None
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
                try:
                    # 民國年轉西元年
                    if len(date_str) == 7:  # 例如：1120101
                        year = int(date_str[:3]) + 1911
                        month = int(date_str[3:5])
                        day = int(date_str[5:7])
                        date_obj = datetime(year, month, day)
                        break
                    else:
                        date_obj = datetime.strptime(date_str, fmt)
                        break
                except ValueError:
                    continue

            if date_obj and date_obj >= cutoff_date:
                filtered.append(row)

        except Exception as exc:
            logger.warning(f"日期解析失敗 | date={row.get('交易年月日')} | error={exc}")
            continue

    return filtered


def convert_to_transactions(data: List[Dict[str, str]]) -> List[Transaction]:
    """
    將 CSV 數據轉換為 Transaction 物件。

    Args:
        data: CSV 數據列表

    Returns:
        Transaction 物件列表
    """
    transactions = []

    for row in data:
        try:
            # 提取欄位
            district = row.get("鄉鎮市區", "").strip()
            road = row.get("土地位置建物門牌", "").strip()

            # 總價（元）轉萬元
            price_str = row.get("總價元", "0").replace(",", "")
            price = float(price_str) / 10000 if price_str else 0

            # 建物面積（平方公尺）轉坪
            area_str = row.get("建物移轉總面積平方公尺", "0").replace(",", "")
            building_area = float(area_str) * 0.3025 if area_str else 0

            # 單價（元/平方公尺）轉萬/坪
            unit_price_str = row.get("單價元平方公尺", "0").replace(",", "")
            unit_price = float(unit_price_str) * 0.3025 / 10000 if unit_price_str else 0

            # 土地面積（平方公尺）轉坪
            land_area_str = row.get("土地移轉總面積平方公尺", "0").replace(",", "")
            land_area = float(land_area_str) * 0.3025 if land_area_str else 0

            # 屋齡
            age_str = row.get("屋齡", "")
            building_age = int(float(age_str)) if age_str else None

            # 交易年月（民國年月）
            transaction_date = row.get("交易年月日", "")[:5] if row.get("交易年月日") else ""

            # 建物型態
            building_type = row.get("建物型態", "").strip()

            # 樓層
            floor = row.get("移轉層次", "").strip()

            # 創建 Transaction 物件
            transaction = Transaction(
                district=district,
                road=road,
                price=round(price, 2),
                unit_price=round(unit_price, 2),
                building_area=round(building_area, 2),
                land_area=round(land_area, 2),
                building_age=building_age,
                transaction_date=transaction_date,
                building_type=building_type,
                floor=floor,
            )

            transactions.append(transaction)

        except Exception as exc:
            logger.warning(f"數據轉換失敗 | row={row} | error={exc}")
            continue

    return transactions


# ==================== 輔助函式 ====================

def get_available_districts(data: List[Dict[str, str]]) -> List[str]:
    """
    從 CSV 數據中提取所有可用的地區名稱。

    Args:
        data: CSV 數據列表

    Returns:
        不重複的地區名稱列表（已排序）
    """
    districts = set()
    for row in data:
        district = row.get("鄉鎮市區", "").strip()
        if district:
            districts.add(district)

    return sorted(districts)


def parse_address(address: str) -> Tuple[Optional[str], Optional[int]]:
    """
    解析地址，提取路段名稱和門牌號碼。

    Args:
        address: 完整地址（例如：臺中市北屯區文心路四段100號）

    Returns:
        (road_name, number): 路段名稱和門牌號碼
        例如：("文心路四段", 100)

    Examples:
        "臺中市北屯區文心路四段100號" -> ("文心路四段", 100)
        "臺中市西屯區市政路500號" -> ("市政路", 500)
        "臺中市北屯區昌平路1段50號" -> ("昌平路1段", 50)
    """
    import re

    if not address:
        return None, None

    # 移除縣市、行政區前綴
    address = address.replace("臺中市", "").replace("台中市", "").strip()

    # 移除常見的行政區名稱
    for district in ["北屯區", "西屯區", "南屯區", "中區", "東區", "西區", "南區", "北區"]:
        address = address.replace(district, "")

    address = address.strip()

    # 提取門牌號碼（數字 + 號/之/樓等）
    number_match = re.search(r'(\d+)(?:號|之|樓|-)?', address)
    number = int(number_match.group(1)) if number_match else None

    # 提取路段名稱（在門牌號碼之前的部分）
    if number_match:
        # 取號碼之前的文字作為路段名稱
        road_name = address[:number_match.start()].strip()
        # 清理路段名稱（移除多餘空白）
        road_name = re.sub(r'\s+', '', road_name)
    else:
        # 如果沒有門牌號碼，嘗試提取路名
        road_match = re.search(r'([^區]+?(?:路|街|巷|弄|段))', address)
        road_name = road_match.group(1) if road_match else None

    return road_name, number


def group_by_project(transactions: List[Transaction], proximity_threshold: int = 100) -> List[ProjectGroup]:
    """
    按路段和門牌號碼相近度將交易記錄分組為建案。

    邏輯：
    1. 先按路段分組
    2. 同路段內，門牌號碼相差 ≤ proximity_threshold 的視為同一建案
    3. 門牌號碼差距大的分開展示

    Args:
        transactions: 交易記錄列表
        proximity_threshold: 門牌號碼相近閾值（預設100號）

    Returns:
        建案分組列表（已排序：路段名稱 A-Z，門牌號碼由小到大）
    """
    # 解析每筆交易的地址
    parsed_transactions = []
    for t in transactions:
        road_name, number = parse_address(t.road)
        if road_name:  # 只處理有路段名稱的交易
            parsed_transactions.append({
                "transaction": t,
                "road_name": road_name,
                "number": number or 0,  # 無門牌號碼的設為 0
            })

    # 按路段分組
    road_groups = defaultdict(list)
    for item in parsed_transactions:
        road_groups[item["road_name"]].append(item)

    # 對每個路段內的交易按門牌號碼排序
    for road_name in road_groups:
        road_groups[road_name].sort(key=lambda x: x["number"])

    # 智能分組：同路段內，門牌相近的合併
    project_groups = []

    for road_name in sorted(road_groups.keys()):  # 按路段名稱排序
        items = road_groups[road_name]

        if not items:
            continue

        # 初始化第一組
        current_group = [items[0]]

        for i in range(1, len(items)):
            prev_number = items[i - 1]["number"]
            curr_number = items[i]["number"]

            # 判斷是否應該併入同一組
            if abs(curr_number - prev_number) <= proximity_threshold:
                current_group.append(items[i])
            else:
                # 門牌差距大，創建新組
                project_groups.append(_create_project_group(road_name, current_group))
                current_group = [items[i]]

        # 處理最後一組
        if current_group:
            project_groups.append(_create_project_group(road_name, current_group))

    return project_groups


def _create_project_group(road_name: str, items: List[Dict]) -> ProjectGroup:
    """
    創建建案分組物件。

    Args:
        road_name: 路段名稱
        items: 該組的交易項目列表

    Returns:
        ProjectGroup 物件
    """
    transactions = [item["transaction"] for item in items]
    numbers = [item["number"] for item in items if item["number"] > 0]

    # 計算統計資訊
    transaction_count = len(transactions)
    avg_price = sum(t.price for t in transactions) / transaction_count
    avg_unit_price = sum(t.unit_price for t in transactions) / transaction_count

    # 生成門牌範圍
    if numbers:
        min_number = min(numbers)
        max_number = max(numbers)
        if min_number == max_number:
            address_range = f"{min_number}號"
        else:
            address_range = f"{min_number}-{max_number}號"
    else:
        min_number = 0
        max_number = 0
        address_range = "未知門牌"

    # 生成成交門牌列表
    addresses = []
    for item in items:
        if item["number"] > 0:
            addresses.append(f"#{item['number']}")
        else:
            addresses.append("#未知")

    return ProjectGroup(
        road_name=road_name,
        address_range=address_range,
        min_number=min_number,
        max_number=max_number,
        transaction_count=transaction_count,
        avg_price=round(avg_price, 2),
        avg_unit_price=round(avg_unit_price, 2),
        addresses=addresses,
        transactions=transactions,
    )


# ==================== 主查詢函式 ====================

async def fetch_moi_data(district: str, road: Optional[str] = None) -> List[Transaction]:
    """
    從 CSV 檔案讀取實價登錄數據。

    Args:
        district: 行政區（例如：北屯區）
        road: 路名（可選）

    Returns:
        交易記錄列表

    Raises:
        FileNotFoundError: CSV 檔案不存在
        ValueError: 數據格式錯誤或無數據
    """
    logger.info(f"正在查詢房價數據 | district={district} | road={road}")

    try:
        # 讀取 CSV 數據（帶快取）
        all_data = await load_csv_data()

        # 按地區過濾
        filtered_data = filter_by_district_and_road(all_data, district, road)

        # 檢查地區過濾結果
        if not filtered_data:
            # 如果沒有結果，提示可用地區
            available_districts = get_available_districts(all_data)
            logger.warning(
                f"地區過濾無結果 | 查詢={district} | 可用地區={', '.join(available_districts)}"
            )

            # 拋出帶有建議的錯誤訊息
            districts_list = "、".join(available_districts)
            raise ValueError(
                f"查無「{district}」的交易記錄。\n\n"
                f"CSV 檔案中可用的地區有：{districts_list}\n"
                f"請確認地區名稱是否正確。"
            )

        # 按時間範圍過濾（過去 5 年）
        filtered_data = filter_by_date_range(filtered_data, years=5)

        # 檢查時間過濾結果
        if not filtered_data:
            logger.warning(f"時間過濾後無結果 | district={district} | road={road}")
            raise ValueError(
                f"「{district}」有交易記錄，但過去 5 年內沒有符合條件的數據。\n"
                f"請嘗試查詢其他地區或聯繫管理員更新資料。"
            )

        # 轉換為 Transaction 物件
        transactions = convert_to_transactions(filtered_data)

        logger.info(f"查詢完成 | district={district} | road={road} | 筆數={len(transactions)}")

        return transactions

    except FileNotFoundError:
        # CSV 檔案不存在
        raise
    except ValueError:
        # 數據格式錯誤或查無結果
        raise
    except Exception as exc:
        logger.error(f"查詢失敗 | district={district} | road={road} | error={exc}", exc_info=True)
        raise ValueError(f"查詢失敗：{exc}")


# ==================== 數據分析 ====================

def analyze_transactions(transactions: List[Transaction], area: str) -> PriceStatistics:
    """
    分析交易數據，計算統計資訊。

    Args:
        transactions: 交易記錄列表
        area: 查詢地區

    Returns:
        價格統計資料
    """
    if not transactions:
        raise ValueError("無交易數據可供分析")

    # 計算平均值
    total_transactions = len(transactions)
    avg_price = sum(t.price for t in transactions) / total_transactions
    avg_unit_price = sum(t.unit_price for t in transactions) / total_transactions

    # 計算最大最小值
    prices = [t.price for t in transactions]
    unit_prices = [t.unit_price for t in transactions]

    max_price = max(prices)
    min_price = min(prices)
    max_unit_price = max(unit_prices)
    min_unit_price = min(unit_prices)

    # 計算屋齡中位數
    ages = [t.building_age for t in transactions if t.building_age is not None]
    median_age = sorted(ages)[len(ages) // 2] if ages else None

    # 計算價格趨勢（按年月分組）
    price_by_month: Dict[str, List[float]] = defaultdict(list)
    for t in transactions:
        # 轉換民國年月為西元年月（簡化處理）
        year_month = t.transaction_date[:5]  # 取前5碼（例如：11201 -> 11201）
        price_by_month[year_month].append(t.unit_price)

    # 計算每個月的平均單價
    price_trend = {
        month: sum(prices) / len(prices)
        for month, prices in price_by_month.items()
    }

    # 排序價格趨勢
    price_trend = dict(sorted(price_trend.items()))

    # 計算查詢期間
    if transactions:
        dates = sorted([t.transaction_date for t in transactions])
        query_period = f"{dates[0]} ~ {dates[-1]}"
    else:
        query_period = "N/A"

    # 建案分組（按路段和門牌號碼相近度）
    project_groups = group_by_project(transactions, proximity_threshold=100)
    logger.info(f"建案分組完成 | 總交易={total_transactions} | 分組數={len(project_groups)}")

    return PriceStatistics(
        area=area,
        total_transactions=total_transactions,
        avg_price=round(avg_price, 2),
        avg_unit_price=round(avg_unit_price, 2),
        max_price=round(max_price, 2),
        min_price=round(min_price, 2),
        max_unit_price=round(max_unit_price, 2),
        min_unit_price=round(min_unit_price, 2),
        median_age=median_age,
        price_trend=price_trend,
        query_period=query_period,
        project_groups=project_groups,
    )


# ==================== 主查詢函式 ====================

async def query_price(area: str, use_cache: bool = True) -> PriceStatistics:
    """
    查詢房價統計資料。

    Args:
        area: 查詢地區（例如：北屯、北屯區民族路、台中市西屯區）
        use_cache: 是否使用快取

    Returns:
        價格統計資料

    Raises:
        ValueError: 無法識別的地區或無數據
    """
    # 檢查快取
    if use_cache:
        cached = _price_cache.get(area)
        if cached:
            return cached

    # 正規化地區名稱
    district, road = normalize_area(area)

    if not district:
        # 無法識別地區，提供建議
        suggestions = suggest_similar_areas(area)
        if suggestions:
            raise ValueError(f"無法識別地區「{area}」，您是否要查詢：{', '.join(suggestions)}？")
        else:
            raise ValueError(f"無法識別地區「{area}」，請輸入台中市的行政區或路名")

    # 查詢實價登錄數據
    try:
        transactions = await fetch_moi_data(district, road)
    except Exception as exc:
        logger.error(f"查詢實價登錄失敗 | district={district} | road={road} | error={exc}")
        raise ValueError(f"查詢失敗：{exc}")

    if not transactions:
        raise ValueError(f"查無「{area}」的交易記錄，請嘗試更換查詢條件")

    # 分析數據
    try:
        stats = analyze_transactions(transactions, area)
    except Exception as exc:
        logger.error(f"數據分析失敗 | area={area} | error={exc}")
        raise ValueError(f"數據分析失敗：{exc}")

    # 儲存至快取
    if use_cache:
        _price_cache.set(area, stats)

    return stats


def set_cache_ttl(hours: int) -> None:
    """設定快取有效期限（小時）."""
    global _price_cache
    _price_cache = PriceCache(ttl_hours=hours)
    logger.info(f"快取有效期限已設定為 {hours} 小時")


def clear_cache() -> None:
    """清空快取."""
    _price_cache.clear()
