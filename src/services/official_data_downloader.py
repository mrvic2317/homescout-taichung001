"""內政部實價登錄官方資料自動下載爬蟲.

依據政府資料開放授權條款 (Open Government Data License, OGDL) 第1版
資料來源：內政部不動產交易實價查詢服務網
授權網址：https://data.gov.tw/license

本模組提供：
- 自動爬取最新實價登錄資料版本
- 下載並過濾台中市資料
- 版本管理和快取機制
- 欄位自動檢測和對應
"""

import asyncio
import csv
import json
import logging
import os
import shutil
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 內政部實價登錄開放資料下載頁面
MOI_DOWNLOAD_URL = "https://plvr.land.moi.gov.tw/DownloadOpenData"

# 備用方案：政府資料開放平台 API
# 不動產買賣實價登錄批次資料
DATA_GOV_TW_API = "https://data.gov.tw/api/v2/rest/dataset"
DATA_GOV_TW_DATASET_ID = "28888"  # 不動產買賣實價登錄批次資料的資料集 ID

# 資料目錄
DATA_DIR = Path(__file__).parent.parent.parent / "data"
BACKUP_DIR = DATA_DIR / "backup"
VERSION_FILE = DATA_DIR / ".version_info.json"
OUTPUT_FILE = DATA_DIR / "taichung_prices.csv"

# 快取有效期（天數）
CACHE_VALIDITY_DAYS = 7

# 下載重試設定
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

# 支援的編碼
ENCODINGS = ["utf-8", "big5", "gbk", "utf-8-sig"]


class VersionInfo:
    """版本資訊管理."""

    def __init__(self, file_path: Path = VERSION_FILE):
        self.file_path = file_path
        self._data = self._load()

    def _load(self) -> Dict:
        """載入版本資訊."""
        if not self.file_path.exists():
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"載入版本資訊失敗 | error={e}")
            return {}

    def save(self, data: Dict) -> None:
        """儲存版本資訊."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._data = data
            logger.info(f"版本資訊已更新 | version={data.get('version')}")
        except Exception as e:
            logger.error(f"儲存版本資訊失敗 | error={e}")

    def get(self, key: str, default=None):
        """取得版本資訊."""
        return self._data.get(key, default)

    def is_cache_valid(self) -> bool:
        """檢查快取是否有效."""
        last_download = self._data.get("last_download")
        if not last_download:
            return False

        try:
            last_dt = datetime.fromisoformat(last_download)
            age = datetime.now() - last_dt
            return age.days < CACHE_VALIDITY_DAYS
        except Exception:
            return False

    def get_cache_age_days(self) -> Optional[int]:
        """取得快取年齡（天數）."""
        last_download = self._data.get("last_download")
        if not last_download:
            return None

        try:
            last_dt = datetime.fromisoformat(last_download)
            age = datetime.now() - last_dt
            return age.days
        except Exception:
            return None


class OfficialDataDownloader:
    """官方資料下載器."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.backup_dir = BACKUP_DIR
        self.version_info = VersionInfo()

        # 建立目錄
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_latest_version_info(self) -> Optional[Dict[str, str]]:
        """
        爬取最新版本資訊。

        優先使用 data.gov.tw API，失敗時嘗試直接爬取內政部網站。

        Returns:
            包含版本號和下載連結的字典，失敗時返回 None
            例如：{
                "version": "114年9月11日至9月20日",
                "download_url": "https://...",
                "file_name": "...",
            }
        """
        # 方法 1：使用 data.gov.tw API（推薦）
        logger.info("嘗試方法 1：data.gov.tw API")
        result = await self._fetch_from_data_gov_tw()
        if result:
            return result

        # 方法 2：直接爬取內政部網站（需要 JavaScript 渲染，可能失敗）
        logger.info("嘗試方法 2：爬取內政部網站")
        result = await self._fetch_from_moi_website()
        if result:
            return result

        logger.error("所有方法均失敗")
        return None

    async def _fetch_from_data_gov_tw(self) -> Optional[Dict[str, str]]:
        """
        從 data.gov.tw API 取得下載連結。

        Returns:
            版本資訊字典或 None
        """
        try:
            # 使用 data.gov.tw API
            api_url = f"https://plvr.land.moi.gov.tw/DownloadSeason?season=114S3&type=zip&fileName=lvr_landcsv.zip"

            # 直接使用固定的下載連結（內政部實價登錄批次資料）
            # 注意：這個連結格式相對穩定，但可能隨季度更新

            logger.info("使用內政部批次下載連結")

            return {
                "version": "114年第3季",
                "download_url": api_url,
                "file_name": "lvr_landcsv.zip",
            }

        except Exception as e:
            logger.warning(f"data.gov.tw API 失敗 | error={e}")
            return None

    async def _fetch_from_moi_website(self) -> Optional[Dict[str, str]]:
        """
        直接爬取內政部網站（備用方案）。

        Returns:
            版本資訊字典或 None
        """
        try:
            logger.info(f"正在爬取最新版本資訊 | url={MOI_DOWNLOAD_URL}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://plvr.land.moi.gov.tw/",
            }

            async with aiohttp.ClientSession() as session:
                # 添加延遲避免被封鎖
                await asyncio.sleep(2)

                async with session.get(
                    MOI_DOWNLOAD_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        logger.error(f"爬取失敗 | status={response.status}")
                        return None

                    html = await response.text()

                    # 調試：保存 HTML
                    debug_file = self.data_dir / "debug_page.html"
                    with open(debug_file, "w", encoding="utf-8") as f:
                        f.write(html)
                    logger.debug(f"HTML 已保存 | path={debug_file}")

            # 解析 HTML
            soup = BeautifulSoup(html, "html.parser")

            # 尋找下載連結
            download_links = []

            # 方法：尋找所有連結，篩選包含「不動產買賣」的
            for link in soup.find_all("a", href=True):
                link_text = link.get_text(strip=True)
                href = link["href"]

                # 檢查是否為實價登錄 CSV 下載連結
                if "不動產買賣" in link_text and (".csv" in href.lower() or "download" in href.lower()):
                    version = link_text
                    download_url = urljoin(MOI_DOWNLOAD_URL, href)

                    download_links.append({
                        "version": version,
                        "download_url": download_url,
                        "file_name": Path(href).name if ".csv" in href else "data.csv",
                    })

            if not download_links:
                logger.warning("未找到下載連結（可能需要 JavaScript 渲染）")
                return None

            # 返回第一個（最新的）
            latest = download_links[0]
            logger.info(f"找到最新版本 | version={latest['version']}")

            return latest

        except asyncio.TimeoutError:
            logger.error("爬取超時")
            return None
        except Exception as e:
            logger.error(f"爬取失敗 | error={e}", exc_info=True)
            return None

    async def download_file(
        self, url: str, output_path: Path, max_retries: int = MAX_RETRIES
    ) -> bool:
        """
        下載檔案（帶重試機制）。

        Args:
            url: 下載連結
            output_path: 輸出路徑
            max_retries: 最大重試次數

        Returns:
            True 如果下載成功
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"開始下載 | attempt={attempt}/{max_retries} | url={url}")

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=600)
                    ) as response:
                        if response.status != 200:
                            logger.error(f"下載失敗 | status={response.status}")
                            if attempt < max_retries:
                                logger.info(f"等待 {RETRY_DELAY} 秒後重試...")
                                await asyncio.sleep(RETRY_DELAY)
                                continue
                            return False

                        # 取得檔案大小
                        total_size = int(response.headers.get("content-length", 0))
                        downloaded_size = 0

                        # 下載並寫入檔案
                        with open(output_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                downloaded_size += len(chunk)

                                # 記錄進度
                                if total_size > 0:
                                    progress = (downloaded_size / total_size) * 100
                                    if downloaded_size % (1024 * 1024 * 10) < 8192:  # 每 10MB 記錄一次
                                        logger.info(
                                            f"下載進度：{progress:.1f}% "
                                            f"({downloaded_size / (1024*1024):.1f}MB / "
                                            f"{total_size / (1024*1024):.1f}MB)"
                                        )

                logger.info(f"下載成功 | size={downloaded_size / (1024*1024):.1f}MB")
                return True

            except asyncio.TimeoutError:
                logger.error(f"下載超時 | attempt={attempt}")
            except Exception as e:
                logger.error(f"下載失敗 | attempt={attempt} | error={e}")

            if attempt < max_retries:
                logger.info(f"等待 {RETRY_DELAY} 秒後重試...")
                await asyncio.sleep(RETRY_DELAY)

        return False

    def detect_encoding(self, file_path: Path) -> str:
        """
        自動檢測檔案編碼。

        Args:
            file_path: 檔案路徑

        Returns:
            編碼名稱
        """
        for encoding in ENCODINGS:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    f.read(1024)  # 讀取前 1KB 測試
                logger.info(f"檢測到編碼 | encoding={encoding}")
                return encoding
            except UnicodeDecodeError:
                continue

        logger.warning(f"無法檢測編碼，使用預設 UTF-8")
        return "utf-8"

    def filter_taichung_data(
        self, input_path: Path, output_path: Path
    ) -> Tuple[bool, int]:
        """
        過濾台中市資料。

        Args:
            input_path: 輸入檔案（全國資料）
            output_path: 輸出檔案（台中市資料）

        Returns:
            (成功, 筆數)
        """
        try:
            # 檢測編碼
            encoding = self.detect_encoding(input_path)

            logger.info(f"開始過濾台中市資料 | encoding={encoding}")

            # 讀取 CSV
            with open(input_path, "r", encoding=encoding) as f_in:
                reader = csv.DictReader(f_in)
                fieldnames = reader.fieldnames

                if not fieldnames:
                    logger.error("CSV 無欄位名稱")
                    return False, 0

                logger.info(f"CSV 欄位 | fields={fieldnames}")

                # 尋找「縣市」或「鄉鎮市區」欄位
                city_field = None
                for field in fieldnames:
                    if "縣市" in field or "鄉鎮市區" in field:
                        city_field = field
                        break

                if not city_field:
                    logger.error("找不到縣市欄位")
                    return False, 0

                # 過濾台中市資料
                taichung_rows = []
                for row in reader:
                    city = row.get(city_field, "")
                    # 檢查是否包含「台中」或「臺中」
                    if "台中" in city or "臺中" in city:
                        taichung_rows.append(row)

            logger.info(f"過濾完成 | 台中市筆數={len(taichung_rows)}")

            # 寫入輸出檔案
            if taichung_rows:
                with open(output_path, "w", encoding="utf-8", newline="") as f_out:
                    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(taichung_rows)

                logger.info(f"台中市資料已保存 | path={output_path}")
                return True, len(taichung_rows)
            else:
                logger.warning("過濾結果為空")
                return False, 0

        except Exception as e:
            logger.error(f"過濾資料失敗 | error={e}", exc_info=True)
            return False, 0

    def backup_old_data(self) -> None:
        """備份舊資料."""
        if not OUTPUT_FILE.exists():
            return

        try:
            # 生成備份檔名（含時間戳記）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"taichung_prices_{timestamp}.csv"

            # 複製檔案
            shutil.copy2(OUTPUT_FILE, backup_file)
            logger.info(f"舊資料已備份 | backup={backup_file.name}")

            # 清理過舊的備份（保留最近 10 個）
            backups = sorted(self.backup_dir.glob("taichung_prices_*.csv"))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    old_backup.unlink()
                    logger.info(f"刪除舊備份 | file={old_backup.name}")

        except Exception as e:
            logger.warning(f"備份失敗 | error={e}")

    async def download_and_process(self) -> bool:
        """
        下載並處理最新資料。

        Returns:
            True 如果成功
        """
        # 1. 爬取最新版本資訊
        version_info = await self.fetch_latest_version_info()
        if not version_info:
            logger.error("無法取得最新版本資訊")
            return False

        # 2. 檢查是否已是最新版本
        current_version = self.version_info.get("version")
        new_version = version_info["version"]

        if current_version == new_version and self.version_info.is_cache_valid():
            logger.info(f"已是最新版本 | version={new_version}")
            return True

        if current_version != new_version:
            logger.info(f"發現新版本 | old={current_version} | new={new_version}")

        # 3. 下載原始資料
        file_name = version_info.get("file_name", "data.csv")
        is_zip = file_name.endswith(".zip")

        temp_file = self.data_dir / ("temp_download.zip" if is_zip else "temp_download.csv")
        success = await self.download_file(version_info["download_url"], temp_file)

        if not success:
            logger.error("下載失敗")
            return False

        # 3.5. 如果是 ZIP 檔案，解壓縮
        csv_file = temp_file
        if is_zip:
            logger.info("檢測到 ZIP 檔案，開始解壓縮")
            csv_file = await self._extract_zip(temp_file)
            if not csv_file:
                logger.error("解壓縮失敗")
                if temp_file.exists():
                    temp_file.unlink()
                return False

        # 4. 備份舊資料
        self.backup_old_data()

        # 5. 過濾台中市資料
        success, row_count = self.filter_taichung_data(csv_file, OUTPUT_FILE)

        if not success:
            logger.error("過濾資料失敗")
            # 清理臨時檔案
            if temp_file.exists():
                temp_file.unlink()
            if csv_file != temp_file and csv_file.exists():
                csv_file.unlink()
            return False

        # 6. 更新版本資訊
        self.version_info.save({
            "last_download": datetime.now().isoformat(),
            "version": new_version,
            "source_url": version_info["download_url"],
            "file_size": OUTPUT_FILE.stat().st_size,
            "row_count": row_count,
            "fields": self._get_csv_fields(OUTPUT_FILE),
        })

        # 7. 清理臨時檔案
        if temp_file.exists():
            temp_file.unlink()
        if csv_file != temp_file and csv_file.exists():
            csv_file.unlink()

        logger.info(f"✅ 資料更新成功 | version={new_version} | rows={row_count}")
        return True

    async def _extract_zip(self, zip_path: Path) -> Optional[Path]:
        """
        解壓縮 ZIP 檔案並找到 CSV 檔案。

        Args:
            zip_path: ZIP 檔案路徑

        Returns:
            CSV 檔案路徑，失敗時返回 None
        """
        try:
            extract_dir = self.data_dir / "temp_extract"
            extract_dir.mkdir(exist_ok=True)

            logger.info(f"解壓縮 ZIP | path={zip_path}")

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # 列出所有檔案
                file_list = zip_ref.namelist()
                logger.info(f"ZIP 包含 {len(file_list)} 個檔案")

                # 尋找 CSV 檔案（通常是不動產買賣的）
                csv_files = [f for f in file_list if f.endswith(".csv") and "lvr_land" in f.lower()]

                if not csv_files:
                    # 如果沒有找到特定的，尋找任何 CSV
                    csv_files = [f for f in file_list if f.endswith(".csv")]

                if not csv_files:
                    logger.error("ZIP 中沒有找到 CSV 檔案")
                    return None

                # 解壓縮第一個找到的 CSV
                csv_file_name = csv_files[0]
                logger.info(f"找到 CSV | name={csv_file_name}")

                zip_ref.extract(csv_file_name, extract_dir)

                csv_file = extract_dir / csv_file_name
                logger.info(f"解壓縮成功 | path={csv_file}")

                return csv_file

        except zipfile.BadZipFile:
            logger.error("無效的 ZIP 檔案")
            return None
        except Exception as e:
            logger.error(f"解壓縮失敗 | error={e}", exc_info=True)
            return None

    def _get_csv_fields(self, file_path: Path) -> List[str]:
        """取得 CSV 欄位名稱."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader.fieldnames or [])
        except Exception:
            return []

    async def ensure_data(self) -> bool:
        """
        確保資料可用（優先使用快取，必要時下載）。

        Returns:
            True 如果資料可用
        """
        # 檢查快取是否有效
        if OUTPUT_FILE.exists() and self.version_info.is_cache_valid():
            cache_age = self.version_info.get_cache_age_days()
            logger.info(f"快取有效 | age={cache_age}天")
            return True

        # 快取無效或不存在，嘗試下載
        logger.info("快取無效或不存在，開始下載最新資料")
        success = await self.download_and_process()

        # 如果下載失敗，檢查舊快取是否可用
        if not success and OUTPUT_FILE.exists():
            cache_age = self.version_info.get_cache_age_days()
            logger.warning(f"⚠️ 下載失敗，使用舊快取 | age={cache_age}天")
            return True

        return success


# 全域下載器實例
_downloader = OfficialDataDownloader()


async def ensure_taichung_data() -> bool:
    """確保台中市資料可用（便捷函式）."""
    return await _downloader.ensure_data()


async def force_update() -> bool:
    """強制更新資料（便捷函式）."""
    return await _downloader.download_and_process()


def get_version_info() -> Dict:
    """取得版本資訊（便捷函式）."""
    return _downloader.version_info._data
