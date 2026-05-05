"""端到端验证：多平台爬虫能否正常工作"""
import asyncio
from crawler import crawl, PLATFORM_QQ, PLATFORM_DOUYIN, PLATFORM_BILIBILI


async def main():
    # ── 测试 QQ音乐（网易云） ──
    print(f"\n{'='*40}")
    print(f"测试平台: {PLATFORM_QQ}")
    print(f"{'='*40}")
    for artist in ["孙燕姿", "周杰伦", ""]:
        print(f"\n  歌手: {artist or '(全网热歌榜)'}")
        songs = await crawl(PLATFORM_QQ, artist, 5)
        if songs:
            for s in songs:
                print(f"    {s['song']} - {s['artist']}")
            print(f"  共 {len(songs)} 首 ✓")
        else:
            print(f"  [错误] 未获取到歌曲 ✗")

    # ── 测试抖音热歌榜 ──
    print(f"\n{'='*40}")
    print(f"测试平台: {PLATFORM_DOUYIN}")
    print(f"{'='*40}")
    songs = await crawl(PLATFORM_DOUYIN, top_n=5)
    if songs:
        for s in songs:
            print(f"  {s['song']} - {s['artist']}")
        print(f"共 {len(songs)} 首 ✓")
    else:
        print(f"  [错误] 未获取到歌曲 ✗")

    # ── 测试 B站音乐区热门 ──
    print(f"\n{'='*40}")
    print(f"测试平台: {PLATFORM_BILIBILI}")
    print(f"{'='*40}")
    songs = await crawl(PLATFORM_BILIBILI, top_n=5)
    if songs:
        for s in songs:
            print(f"  {s['song']} - {s['artist']}")
        print(f"共 {len(songs)} 首 ✓")
    else:
        print(f"  [错误] 未获取到歌曲 ✗")

    print(f"\n{'='*40}")
    print("全部测试完成！")


asyncio.run(main())
