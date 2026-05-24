"""novel-agent — AI 驱动的长篇小说写作助手

核心思路：每个人物独立建立 Obsidian Markdown 档案（知识库），
写作时查询人物档案注入 prompt，解决长篇写作中的人物一致性问题。

用法:
    novel-agent project create "我的小说" --genre xianxia
    novel-agent character add "我的小说" 主角名
    novel-agent chapter write "我的小说" 1
"""

if __name__ == "__main__":
    from ui.cli import app
    app()
