"""端到端验证：爬虫能否正常工作"""
import asyncio
from crawler import SongCrawler


async def main():
    crawler = SongCrawler()

    for artist in ["孙燕姿", "周杰伦"]:
        print(f"\n测试歌手: {artist}")
        songs = await crawler.search_top_songs(artist, 5)
        if songs:
            for s in songs:
                print(f"  {s['song']} - {s['artist']}")
            print(f"共 {len(songs)} 首 ✓")
        else:
            print(f"  [错误] 未获取到歌曲 ✗")


asyncio.run(main())
