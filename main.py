"""novel-agent — AI 驱动的长篇小说写作助手

核心思路：每个人物独立建立 Obsidian Markdown 档案（知识库），
写作时查询人物档案注入 prompt，解决长篇写作中的人物一致性问题。

用法:
    python main.py project create --name "长安录" --genre "架空历史权谋"
    python main.py character add --project "长安录" --name "林晚秋"
    python main.py chapter write --project "长安录" --num 1
"""

__version__ = "0.1.0"

if __name__ == "__main__":
    from ui.cli import app
    app()
