"""測試官方資料下載器功能."""
import asyncio
import logging
from pathlib import Path
from src.services import official_data_downloader

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')


async def test_1_fetch_version_info():
    """測試 1：爬取最新版本資訊."""
    print("\n" + "="*60)
    print("測試 1：爬取最新版本資訊")
    print("="*60)
    print("  使用備用方案：內政部批次下載連結")

    downloader = official_data_downloader.OfficialDataDownloader()

    try:
        version_info = await downloader.fetch_latest_version_info()

        if version_info:
            print(f"  ✅ 成功爬取版本資訊")
            print(f"     版本：{version_info['version']}")
            print(f"     下載連結：{version_info['download_url'][:100]}...")
            print(f"     檔案名稱：{version_info['file_name']}")

            # 檢查是否為 ZIP 檔案
            if version_info['file_name'].endswith('.zip'):
                print(f"     ⚠️ 檔案類型：ZIP（需要解壓縮）")
        else:
            print(f"  ⚠️ 未找到版本資訊（可能是網路問題或網站結構變更）")

    except Exception as e:
        print(f"  ❌ 爬取失敗：{e}")


async def test_2_check_cache():
    """測試 2：檢查快取狀態."""
    print("\n" + "="*60)
    print("測試 2：檢查快取狀態")
    print("="*60)

    version_info = official_data_downloader.VersionInfo()

    # 檢查快取是否有效
    is_valid = version_info.is_cache_valid()
    cache_age = version_info.get_cache_age_days()

    print(f"  快取有效：{'✅ 是' if is_valid else '❌ 否'}")

    if cache_age is not None:
        print(f"  快取年齡：{cache_age} 天")
        print(f"  最後下載：{version_info.get('last_download')}")
        print(f"  版本：{version_info.get('version')}")
        print(f"  資料筆數：{version_info.get('row_count')}")
    else:
        print(f"  尚無快取資料")


async def test_3_encoding_detection():
    """測試 3：編碼檢測."""
    print("\n" + "="*60)
    print("測試 3：檔案編碼檢測")
    print("="*60)

    downloader = official_data_downloader.OfficialDataDownloader()

    # 檢查現有 CSV 檔案
    csv_file = Path("data/taichung_prices.csv")

    if csv_file.exists():
        encoding = downloader.detect_encoding(csv_file)
        print(f"  檔案：{csv_file}")
        print(f"  檢測到編碼：{encoding}")
    else:
        print(f"  ⚠️ 檔案不存在：{csv_file}")


async def test_4_filter_data():
    """測試 4：資料過濾（模擬）."""
    print("\n" + "="*60)
    print("測試 4：台中市資料過濾")
    print("="*60)

    print("  ⚠️ 此測試需要實際下載的全國資料")
    print("  如果有 temp_download.csv，將嘗試過濾")

    downloader = official_data_downloader.OfficialDataDownloader()

    temp_file = Path("data/temp_download.csv")
    output_file = Path("data/test_filtered.csv")

    if temp_file.exists():
        success, row_count = downloader.filter_taichung_data(temp_file, output_file)

        if success:
            print(f"  ✅ 過濾成功 | 台中市筆數={row_count}")

            if output_file.exists():
                output_file.unlink()  # 清理測試檔案
        else:
            print(f"  ❌ 過濾失敗")
    else:
        print(f"  ⏭️ 跳過測試（無測試資料）")


async def test_5_ensure_data():
    """測試 5：確保資料可用（完整流程）."""
    print("\n" + "="*60)
    print("測試 5：確保資料可用（完整流程）")
    print("="*60)
    print("  ⚠️ 此測試會嘗試下載真實資料，請謹慎執行")
    print("  如果快取有效，將直接使用快取")

    user_input = input("\n  是否執行此測試？(y/N): ")

    if user_input.lower() != 'y':
        print("  ⏭️ 跳過測試")
        return

    try:
        downloader = official_data_downloader.OfficialDataDownloader()

        # 嘗試確保資料可用
        success = await downloader.ensure_data()

        if success:
            print(f"  ✅ 資料已就緒")

            # 顯示檔案資訊
            output_file = Path("data/taichung_prices.csv")
            if output_file.exists():
                size_mb = output_file.stat().st_size / (1024 * 1024)
                print(f"     檔案大小：{size_mb:.2f} MB")

            # 顯示版本資訊
            version_info = official_data_downloader.get_version_info()
            if version_info:
                print(f"     版本：{version_info.get('version')}")
                print(f"     資料筆數：{version_info.get('row_count')}")
        else:
            print(f"  ❌ 資料無法取得")

    except Exception as e:
        print(f"  ❌ 測試失敗：{e}")


async def test_6_version_file():
    """測試 6：版本資訊檔案."""
    print("\n" + "="*60)
    print("測試 6：版本資訊檔案 (.version_info.json)")
    print("="*60)

    version_file = Path("data/.version_info.json")

    if version_file.exists():
        print(f"  ✅ 版本檔案存在")

        import json
        with open(version_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"     版本：{data.get('version')}")
        print(f"     最後下載：{data.get('last_download')}")
        print(f"     資料筆數：{data.get('row_count')}")
        print(f"     檔案大小：{data.get('file_size') / (1024*1024):.2f} MB" if data.get('file_size') else "     檔案大小：未知")

        fields = data.get('fields', [])
        if fields:
            print(f"     欄位數量：{len(fields)}")
            print(f"     欄位範例：{', '.join(fields[:5])}...")
    else:
        print(f"  ⚠️ 版本檔案不存在（尚未下載資料）")


async def test_7_backup_system():
    """測試 7：備份系統."""
    print("\n" + "="*60)
    print("測試 7：備份系統")
    print("="*60)

    backup_dir = Path("data/backup")

    if backup_dir.exists():
        backups = list(backup_dir.glob("taichung_prices_*.csv"))

        print(f"  備份目錄存在：{backup_dir}")
        print(f"  備份檔案數量：{len(backups)}")

        if backups:
            # 顯示最近 3 個備份
            recent_backups = sorted(backups)[-3:]
            print(f"\n  最近的備份：")
            for backup in recent_backups:
                size_mb = backup.stat().st_size / (1024 * 1024)
                print(f"    - {backup.name} ({size_mb:.2f} MB)")
    else:
        print(f"  ⚠️ 備份目錄不存在")


async def main():
    """主測試函式."""
    print("\n" + "🚀 開始測試官方資料下載器 " + "🚀")

    # 1. 爬取版本資訊
    await test_1_fetch_version_info()

    # 2. 檢查快取狀態
    await test_2_check_cache()

    # 3. 編碼檢測
    await test_3_encoding_detection()

    # 4. 資料過濾（跳過，需要實際資料）
    await test_4_filter_data()

    # 5. 確保資料可用（互動式，需要用戶確認）
    await test_5_ensure_data()

    # 6. 版本資訊檔案
    await test_6_version_file()

    # 7. 備份系統
    await test_7_backup_system()

    print("\n" + "="*60)
    print("🎉 測試完成")
    print("="*60)

    print("\n💡 使用說明：")
    print("   1. 首次執行會嘗試下載最新資料（需網路）")
    print("   2. 下載成功後，資料會快取 7 天")
    print("   3. 舊資料會自動備份到 data/backup/")
    print("   4. 版本資訊記錄在 data/.version_info.json")
    print("   5. 如需強制更新，執行：")
    print("      python3 -c 'import asyncio; from src.services import official_data_downloader; asyncio.run(official_data_downloader.force_update())'")
    print()


if __name__ == "__main__":
    asyncio.run(main())
