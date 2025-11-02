"""政府開放資料自動下載服務.

支援：
- 多城市資料來源配置
- 7 天快取機制
- 自動下載和更新
- 錯誤處理和降級策略
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger(__name__)

# 資料來源配置
# 注意：以下 URL 為範例，實際使用時需替換為真實的政府開放資料連結
DATA_SOURCES = {
    "taichung": {
        "name": "台中市",
        "url": "https://data.gov.tw/api/v2/rest/dataset/export?dataset_id=XXXXX",
        "filename": "taichung_prices.csv",
        "description": "台中市不動產買賣實價登錄",
    },
    "taipei": {
        "name": "台北市",
        "url": "https://data.gov.tw/api/v2/rest/dataset/export?dataset_id=XXXXX",
        "filename": "taipei_prices.csv",
        "description": "台北市不動產買賣實價登錄",
    },
    "new_taipei": {
        "name": "新北市",
        "url": "https://data.gov.tw/api/v2/rest/dataset/export?dataset_id=XXXXX",
        "filename": "new_taipei_prices.csv",
        "description": "新北市不動產買賣實價登錄",
    },
    "kaohsiung": {
        "name": "高雄市",
        "url": "https://data.gov.tw/api/v2/rest/dataset/export?dataset_id=XXXXX",
        "filename": "kaohsiung_prices.csv",
        "description": "高雄市不動產買賣實價登錄",
    },
}

# 快取有效期（天數）
CACHE_VALIDITY_DAYS = 7

# 資料目錄
DATA_DIR = Path(__file__).parent.parent.parent / "data"


class DataDownloader:
    """政府開放資料下載器."""

    def __init__(self, data_dir: Path = DATA_DIR):
        """初始化下載器.

        Args:
            data_dir: 資料存放目錄
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, city_key: str) -> Path:
        """取得城市資料檔案路徑.

        Args:
            city_key: 城市鍵值（例如：taichung）

        Returns:
            檔案完整路徑
        """
        source = DATA_SOURCES.get(city_key)
        if not source:
            raise ValueError(f"不支援的城市：{city_key}")

        return self.data_dir / source["filename"]

    def _is_cache_valid(self, file_path: Path) -> bool:
        """檢查快取是否有效.

        Args:
            file_path: 檔案路徑

        Returns:
            True 如果快取有效（檔案存在且未過期）
        """
        if not file_path.exists():
            logger.info(f"快取檔案不存在 | path={file_path}")
            return False

        # 檢查檔案修改時間
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - mtime
        is_valid = age.days < CACHE_VALIDITY_DAYS

        if is_valid:
            logger.info(
                f"快取仍有效 | path={file_path.name} | age={age.days}天 | "
                f"valid_until={CACHE_VALIDITY_DAYS}天"
            )
        else:
            logger.info(
                f"快取已過期 | path={file_path.name} | age={age.days}天 | "
                f"expired_after={CACHE_VALIDITY_DAYS}天"
            )

        return is_valid

    async def download_city_data(
        self, city_key: str, force: bool = False
    ) -> Optional[Path]:
        """下載城市資料.

        Args:
            city_key: 城市鍵值（例如：taichung）
            force: 是否強制重新下載（忽略快取）

        Returns:
            下載後的檔案路徑，失敗時返回 None
        """
        source = DATA_SOURCES.get(city_key)
        if not source:
            logger.error(f"❌ 不支援的城市 | city={city_key}")
            return None

        file_path = self._get_file_path(city_key)

        # 檢查快取
        if not force and self._is_cache_valid(file_path):
            logger.info(f"✅ 使用快取資料 | city={source['name']} | path={file_path.name}")
            return file_path

        # 下載資料
        logger.info(f"🔄 開始下載資料 | city={source['name']} | url={source['url']}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    source["url"], timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        logger.error(
                            f"❌ 下載失敗 | city={source['name']} | "
                            f"status={response.status}"
                        )
                        # 如果下載失敗且有舊快取，使用舊快取
                        if file_path.exists():
                            logger.warning(
                                f"⚠️ 下載失敗，使用舊快取 | city={source['name']} | "
                                f"path={file_path.name}"
                            )
                            return file_path
                        return None

                    # 讀取內容
                    content = await response.read()

                    # 儲存檔案
                    with open(file_path, "wb") as f:
                        f.write(content)

                    # 記錄成功
                    size_mb = len(content) / (1024 * 1024)
                    logger.info(
                        f"✅ 下載成功 | city={source['name']} | "
                        f"size={size_mb:.2f}MB | path={file_path.name}"
                    )

                    return file_path

        except asyncio.TimeoutError:
            logger.error(f"❌ 下載超時 | city={source['name']} | timeout=300秒")
        except aiohttp.ClientError as e:
            logger.error(f"❌ 網路連線錯誤 | city={source['name']} | error={e}")
        except Exception as e:
            logger.error(f"❌ 下載失敗 | city={source['name']} | error={e}")

        # 下載失敗，嘗試使用舊快取
        if file_path.exists():
            logger.warning(
                f"⚠️ 下載失敗，使用舊快取 | city={source['name']} | "
                f"path={file_path.name}"
            )
            return file_path

        return None

    async def download_all_cities(self, force: bool = False) -> Dict[str, Optional[Path]]:
        """下載所有城市資料.

        Args:
            force: 是否強制重新下載（忽略快取）

        Returns:
            城市鍵值 -> 檔案路徑的字典
        """
        logger.info(f"🚀 開始下載所有城市資料 | cities={len(DATA_SOURCES)} | force={force}")

        tasks = [
            self.download_city_data(city_key, force=force)
            for city_key in DATA_SOURCES.keys()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 整理結果
        downloads = {}
        for city_key, result in zip(DATA_SOURCES.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"❌ 下載失敗 | city={city_key} | error={result}")
                downloads[city_key] = None
            else:
                downloads[city_key] = result

        # 統計
        success_count = sum(1 for path in downloads.values() if path is not None)
        logger.info(
            f"📊 下載完成 | total={len(DATA_SOURCES)} | "
            f"success={success_count} | failed={len(DATA_SOURCES) - success_count}"
        )

        return downloads

    async def ensure_city_data(self, city_key: str) -> Optional[Path]:
        """確保城市資料可用（優先使用快取，必要時下載）.

        這是最常用的方法，會：
        1. 檢查快取是否有效
        2. 若快取有效，直接返回
        3. 若快取無效或不存在，下載新資料

        Args:
            city_key: 城市鍵值（例如：taichung）

        Returns:
            資料檔案路徑，失敗時返回 None
        """
        return await self.download_city_data(city_key, force=False)

    def get_available_cities(self) -> Dict[str, str]:
        """取得所有可用城市清單.

        Returns:
            城市鍵值 -> 城市名稱的字典
        """
        return {key: source["name"] for key, source in DATA_SOURCES.items()}

    def get_cache_info(self, city_key: str) -> Optional[Dict[str, any]]:
        """取得快取資訊.

        Args:
            city_key: 城市鍵值

        Returns:
            包含快取資訊的字典，檔案不存在時返回 None
        """
        source = DATA_SOURCES.get(city_key)
        if not source:
            return None

        file_path = self._get_file_path(city_key)
        if not file_path.exists():
            return None

        stat = file_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        age = datetime.now() - mtime
        is_valid = age.days < CACHE_VALIDITY_DAYS

        return {
            "city": source["name"],
            "file_path": str(file_path),
            "file_size_mb": stat.st_size / (1024 * 1024),
            "last_modified": mtime.strftime("%Y-%m-%d %H:%M:%S"),
            "age_days": age.days,
            "is_valid": is_valid,
            "expires_in_days": max(0, CACHE_VALIDITY_DAYS - age.days),
        }


# 全域下載器實例
_downloader = DataDownloader()


async def download_taichung_data(force: bool = False) -> Optional[Path]:
    """下載台中市資料（便捷函式）.

    Args:
        force: 是否強制重新下載

    Returns:
        檔案路徑
    """
    return await _downloader.download_city_data("taichung", force=force)


async def ensure_taichung_data() -> Optional[Path]:
    """確保台中市資料可用（便捷函式）.

    優先使用官方下載器（爬取最新資料），失敗時使用舊方法。

    Returns:
        檔案路徑
    """
    try:
        # 優先使用官方下載器
        from . import official_data_downloader

        logger.info("使用官方下載器獲取資料")
        success = await official_data_downloader.ensure_taichung_data()

        if success:
            output_file = DATA_DIR / "taichung_prices.csv"
            if output_file.exists():
                logger.info(f"✅ 官方資料已就緒 | path={output_file}")
                return output_file

    except ImportError:
        logger.warning("官方下載器不可用，使用舊方法")
    except Exception as e:
        logger.warning(f"官方下載器失敗 | error={e}")

    # 降級：使用舊方法
    logger.info("降級使用舊下載方法")
    return await _downloader.ensure_city_data("taichung")


async def download_all_cities(force: bool = False) -> Dict[str, Optional[Path]]:
    """下載所有城市資料（便捷函式）.

    Args:
        force: 是否強制重新下載

    Returns:
        城市 -> 檔案路徑的字典
    """
    return await _downloader.download_all_cities(force=force)


def get_taichung_cache_info() -> Optional[Dict[str, any]]:
    """取得台中市快取資訊（便捷函式）.

    優先返回官方下載器的版本資訊，失敗時使用舊方法。

    Returns:
        快取資訊字典
    """
    try:
        # 優先使用官方下載器的版本資訊
        from . import official_data_downloader

        version_info = official_data_downloader.get_version_info()
        if version_info:
            # 轉換格式以匹配舊的介面
            output_file = DATA_DIR / "taichung_prices.csv"
            if output_file.exists():
                stat = output_file.stat()
                last_download = version_info.get("last_download")

                if last_download:
                    from datetime import datetime
                    try:
                        mtime = datetime.fromisoformat(last_download)
                        age = datetime.now() - mtime

                        return {
                            "city": "台中市",
                            "file_path": str(output_file),
                            "file_size_mb": stat.st_size / (1024 * 1024),
                            "last_modified": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                            "age_days": age.days,
                            "is_valid": age.days < CACHE_VALIDITY_DAYS,
                            "expires_in_days": max(0, CACHE_VALIDITY_DAYS - age.days),
                            "version": version_info.get("version"),
                            "row_count": version_info.get("row_count"),
                            "source": "official",  # 標記來源
                        }
                    except Exception:
                        pass

    except Exception as e:
        logger.debug(f"無法取得官方下載器資訊 | error={e}")

    # 降級：使用舊方法
    return _downloader.get_cache_info("taichung")
