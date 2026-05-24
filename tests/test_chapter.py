"""测试 chapter 模块"""

import pytest
from knowledge.chapter import _chinese_num, ChapterManager


class TestChineseNum:
    def test_single_digit(self):
        assert _chinese_num(1) == "一"
        assert _chinese_num(5) == "五"
        assert _chinese_num(9) == "九"

    def test_teens(self):
        assert _chinese_num(10) == "十"
        assert _chinese_num(11) == "十一"
        assert _chinese_num(19) == "十九"

    def test_tens(self):
        assert _chinese_num(20) == "二十"
        assert _chinese_num(25) == "二十五"
        assert _chinese_num(99) == "九十九"

    def test_hundreds(self):
        assert _chinese_num(100) == "一百"
        assert _chinese_num(120) == "一百二十"
        assert _chinese_num(500) == "五百"

    def test_edge_cases(self):
        assert _chinese_num(0) == "0"
        assert _chinese_num(1000) == "1000"


class TestChapterManagerSorting:
    def test_sorted_key(self, tmp_path):
        chm = ChapterManager(tmp_path)
        # 创建章节文件
        for n in [1, 2, 10, 11, 3, 20, 100]:
            f = tmp_path / "chapters" / f"ch{n:02d}.md" if n < 100 else tmp_path / "chapters" / f"ch{n}.md"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"---\nchapter: {n}\ntitle: Ch{n}\n---\n\nbody", encoding="utf-8")

        chapters = chm._sorted_chapters()
        nums = []
        import re
        for ch in chapters:
            m = re.search(r"ch(\d+)", ch.stem)
            if m:
                nums.append(int(m.group(1)))
        assert nums == sorted(nums)
