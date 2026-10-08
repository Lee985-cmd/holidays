"""
Twitter (X) 自动发帖脚本
基于 Playwright，保留浏览器登录态，首次手动登录后可自动发帖。

用法：
  # 首次：登录（会打开浏览器，手动登录一次后关闭）
  python twitter_bot.py login

  # 发一条推文（从 tweets.txt 取一条）
  python twitter_bot.py post

  # 定时发帖（每天 9:00 和 18:00 各发一条）
  python twitter_bot.py schedule
"""
import sys
import os
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_DIR = Path(__file__).parent
PROFILE_DIR = BASE_DIR / "twitter_profile"
TWEETS_FILE = BASE_DIR / "tweets.txt"
POSTED_FILE = BASE_DIR / "posted_tweets.txt"


def load_tweets():
    """从 tweets.txt 读取待发推文列表。"""
    if not TWEETS_FILE.exists():
        return []
    with open(TWEETS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def save_tweets(tweets):
    """写回剩余推文。"""
    with open(TWEETS_FILE, "w", encoding="utf-8") as f:
        for t in tweets:
            f.write(t + "\n")


def mark_posted(tweet):
    """记录已发推文。"""
    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(tweet + "\n")


def login():
    """首次登录：打开浏览器让用户手动登录。"""
    PROFILE_DIR.mkdir(exist_ok=True)
    print("正在打开 Twitter，请手动登录...")
    print("登录成功后直接关闭浏览器窗口即可，登录态会保存。")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.goto("https://twitter.com/login")
        print("浏览器已打开，请在浏览器中完成登录。")
        print("登录后关闭浏览器窗口，脚本会自动退出。")
        # 等待用户关闭浏览器
        input("登录完成后按回车键退出...")
        context.close()
    print("登录态已保存到:", PROFILE_DIR)


def post_tweet(tweet_text):
    """发布一条推文。返回 True 成功，False 失败。"""
    if not PROFILE_DIR.exists():
        print("错误：未找到登录态，请先运行: python twitter_bot.py login")
        return False

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=True,
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        try:
            page.goto("https://twitter.com/compose/post", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)

            # 等待推文输入框
            editor = page.locator("[data-testid='tweetTextarea_0']")
            editor.wait_for(timeout=15000)

            # 输入推文内容
            editor.click()
            editor.fill(tweet_text)

            # 点击发布按钮
            post_btn = page.locator("[data-testid='tweetButton']")
            post_btn.wait_for(timeout=5000)
            post_btn.click()

            # 等待发布完成（URL 变化或出现成功提示）
            page.wait_for_timeout(3000)

            print("✅ 推文已发布:")
            print(tweet_text[:100] + ("..." if len(tweet_text) > 100 else ""))
            return True

        except PWTimeout:
            print("❌ 超时：页面加载或元素查找失败")
            print("可能原因：登录态过期，请重新运行 python twitter_bot.py login")
            return False
        except Exception as e:
            print(f"❌ 发布失败: {e}")
            return False
        finally:
            context.close()


def post_one():
    """从队列取一条推文发布。"""
    tweets = load_tweets()
    if not tweets:
        print("推文队列为空，请在 tweets.txt 中添加内容。")
        return

    # 随机选一条（避免总是按顺序发）
    tweet = random.choice(tweets)
    if post_tweet(tweet):
        # 从队列移除，记录到已发
        tweets.remove(tweet)
        save_tweets(tweets)
        mark_posted(tweet)
        print(f"剩余推文: {len(tweets)} 条")
    else:
        print("发布失败，推文未从队列移除。")


def schedule_posts():
    """定时发帖：每天 9:00 和 18:00 各发一条。"""
    import schedule
    import time

    print("定时任务已启动，每天 09:00 和 18:00 各发一条推文。")
    print("按 Ctrl+C 停止。")

    def job():
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 执行定时发帖...")
        post_one()

    schedule.every().day.at("09:00").do(job)
    schedule.every().day.at("18:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "login":
        login()
    elif cmd == "post":
        post_one()
    elif cmd == "schedule":
        schedule_posts()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
