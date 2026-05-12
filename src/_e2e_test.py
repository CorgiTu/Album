"""端到端验证：多平台爬虫能否正常工作"""
import asyncio
from crawler import crawl, get_all_platforms


async def test_platform(name: str):
    print(f"\n{'='*40}")
    print(f"测试平台: {name}")
    print(f"{'='*40}")
    if name in ("抖音热歌榜", "B站音乐区热门", "汽水音乐"):
        songs = await crawl(name, top_n=5)
        if songs:
            for s in songs:
                print(f"  {s['song']} - {s['artist']}")
            print(f"共 {len(songs)} 首 ✓")
        else:
            print(f"  [错误] 未获取到歌曲 ✗")
    else:
        for artist in ["孙燕姿", "周杰伦", ""]:
            print(f"\n  歌手: {artist or '(全网热歌榜)'}")
            songs = await crawl(name, artist, 5)
            if songs:
                for s in songs:
                    print(f"    {s['song']} - {s['artist']}")
                print(f"  共 {len(songs)} 首 ✓")
            else:
                print(f"  [错误] 未获取到歌曲 ✗")


async def main():
    platforms = get_all_platforms()
    print(f"发现 {len(platforms)} 个平台: {platforms}")

    for name in platforms:
        await test_platform(name)

    # 测试多歌手聚合（仅测试 mock 平台）
    print(f"\n{'='*40}")
    print("测试多歌手聚合（汽水音乐）")
    print(f"{'='*40}")
    from plugins import get_crawler
    crawler_inst = get_crawler("汽水音乐")
    if crawler_inst:
        artists = ["周杰伦", "孙燕姿"]
        all_songs = []
        for a in artists:
            songs = await crawler_inst.fetch(a, 5)
            all_songs.extend(songs)
            print(f"  {a}: 获取 {len(songs)} 首")
        print(f"  聚合后共 {len(all_songs)} 首 ✓")

    print(f"\n{'='*40}")
    print("全部测试完成！")


asyncio.run(main())
