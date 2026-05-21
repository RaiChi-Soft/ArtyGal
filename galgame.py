#!/usr/bin/env python3
"""
《炽焰炮阵：铸锋少年》GALGAME - TUI互动视觉小说
使用 Textual 框架构建，支持 ANSI 角色立绘、多线剧情、好感度与成就系统
"""

from __future__ import annotations

import json
import os
import re
import sys
import ctypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.ansi import AnsiDecoder
from rich.text import Text
from rich.style import Style
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Button, Label, Header, Footer
from textual.screen import Screen, ModalScreen
from textual.reactive import reactive
from textual.binding import Binding
from textual import events


# ============================================================
# 常量定义
# ============================================================

# 角色名称映射 (ANSI文件名 -> 中文名)
CHARACTER_MAP: Dict[str, str] = {
    "sl": "苏凛",
    "xr": "夏燃",
    "wy": "温屿",
    "qy": "秋柚",
    "xg": "小G",
}

# 角色ANSI文件名列表
CHARACTER_FILES: List[str] = ["sl", "xr", "wy", "qy", "xg"]

# 场景背景ANSI文件名映射 (剧情 bg -> ANSI文件名)
SCENE_ART_MAP: Dict[str, str] = {
    "school": "school",
    "workshop": "workshop",
    "range": "range",
}

def resource_path(relative_path: str) -> Path:
    """获取开发环境或 PyInstaller 打包环境下的资源路径。"""
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


# 资源目录
RESOURCE_DIR: Path = resource_path("resources")
ANSI_DIR: Path = RESOURCE_DIR
MUSIC_FILE: Path = RESOURCE_DIR / "Drafting_the_Final_Gear.mp3"

DISCLAIMER_TEXT = "本故事纯属虚构，如有雷同纯属巧合。\n弘扬正能量，做新时代好青年。"

# 存档文件路径
SAVE_FILE: Path = Path("save_data.json")

# ============================================================
# ANSI 资源加载工具
# ============================================================


def load_ansi_art(file_path: Path) -> Text:
    """加载 .ans 文件，返回保留 ANSI 样式的 Rich Text 对象"""
    if not file_path.exists():
        return Text(f"[{file_path.stem} 无图像]", style=Style(color="grey53"))
    try:
        raw = file_path.read_bytes()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("cp437")
        decoder = AnsiDecoder()
        lines: List[Text] = []
        for raw_line in content.splitlines():
            decoded_line = next(decoder.decode(raw_line), Text(""))
            lines.append(decoded_line)
        if not lines:
            return Text("")
        art = Text()
        for index, line in enumerate(lines):
            if index:
                art.append("\n")
            art.append_text(line)
        return art
    except Exception:
        return Text(f"[{file_path.stem} 加载失败]", style=Style(color="red"))


def get_character_art(char_id: str) -> Text:
    """根据角色ID获取ANSI立绘"""
    path = ANSI_DIR / f"{char_id}.ans"
    return load_ansi_art(path)


def get_scene_art(bg_id: str) -> Text:
    """根据剧情背景ID获取ANSI场景图"""
    file_stem = SCENE_ART_MAP.get(bg_id, bg_id)
    path = ANSI_DIR / f"{file_stem}.ans"
    return load_ansi_art(path)


# ============================================================
# 背景音乐
# ============================================================


class AudioManager:
    """使用 Windows MCI 播放循环 MP3；其它平台自动降级为静音。"""

    def __init__(self, music_path: Path) -> None:
        self.music_path = music_path
        self.enabled = True
        self.volume = 55
        self._alias = "artygal_bgm"
        self._opened = False
        self._available = sys.platform.startswith("win")

    def _mci(self, command: str) -> int:
        if not self._available:
            return 1
        return ctypes.windll.winmm.mciSendStringW(command, None, 0, None)

    def start(self) -> None:
        if not self.enabled or not self._available or not self.music_path.exists():
            return
        if not self._opened:
            escaped = str(self.music_path).replace('"', "")
            if self._mci(f'open "{escaped}" type mpegvideo alias {self._alias}') != 0:
                self._available = False
                return
            self._opened = True
        self.set_volume(self.volume)
        self._mci(f"play {self._alias} repeat")

    def stop(self) -> None:
        if self._opened:
            self._mci(f"stop {self._alias}")

    def close(self) -> None:
        if self._opened:
            self._mci(f"stop {self._alias}")
            self._mci(f"close {self._alias}")
            self._opened = False

    def toggle(self) -> None:
        self.enabled = not self.enabled
        if self.enabled:
            self.start()
        else:
            self.stop()

    def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, volume))
        if self._opened:
            self._mci(f"setaudio {self._alias} volume to {self.volume * 10}")

    def volume_down(self) -> None:
        self.set_volume(self.volume - 10)

    def volume_up(self) -> None:
        self.set_volume(self.volume + 10)


# ============================================================
# 剧情数据
# ============================================================

# 完整剧情大纲解析
STORY_SCRIPT: List[dict] = [
    # ===== 第一章：入学逢炮，初心立誓 =====
    {
        "chapter": 1,
        "title": "第一章：入学逢炮，初心立誓",
        "scenes": [
            {
                "id": "ch1_1",
                "narrator": True,
                "text": "锋焰高等学园，全国闻名的军械工科名校。",
                "characters": [],
                "bg": "school",
            },
            {
                "id": "ch1_2",
                "narrator": True,
                "text": "校园里，机甲社、轻武器社的招新摊位热闹非凡，人流如织。",
                "characters": [],
                "bg": "school",
            },
            {
                "id": "ch1_3",
                "text": "机甲？轻武器？不，我只想研究火炮。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "school",
            },
            {
                "id": "ch1_4",
                "narrator": True,
                "text": "小G径直穿过人潮，走向校园深处一处旧楼。门牌上歪歪斜斜地写着——「火炮同好社」。",
                "characters": [],
                "bg": "school",
            },
            {
                "id": "ch1_5",
                "narrator": True,
                "text": "推开门的瞬间，小G愣住了——破旧的工作室内，几个女生正围着一门老式榴弹炮忙碌。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch1_6",
                "text": "你就是……新来的？是来嘲笑我们的，还是真的想加入？",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "workshop",
            },
            {
                "id": "ch1_7",
                "text": "我想加入。我想……打造最强的火炮。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "workshop",
            },
            {
                "id": "ch1_8",
                "narrator": True,
                "text": "苏凛挑了挑眉毛，将一把游标卡尺递到小G面前。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch1_9",
                "text": "那就证明给我看。这门M101的炮膛磨损量，用这把卡尺测出来，误差超过0.02毫米就去机甲社报到吧。",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "workshop",
            },
            {
                "id": "ch1_10",
                "narrator": True,
                "text": "小G接过卡尺，深吸一口气，俯身在炮管旁仔细测量起来。",
                "characters": [],
                "bg": "workshop",
                "choices": [
                    {"text": "全神贯注反复测量三次取平均值", "next": "ch1_11a", "affection": {"sl": 2}, "achievement": "求是"},
                    {"text": "凭手感直接报出一个近似值", "next": "ch1_11b", "affection": {}},
                ],
            },
        ],
    },
    # 第一章分支A：认真测量
    {
        "chapter": 1,
        "title": "第一章：入学逢炮，初心立誓",
        "scenes": [
            {
                "id": "ch1_11a",
                "narrator": True,
                "text": "小G反复测量三次——0.07毫米。苏凛接过卡尺，嘴角微微上扬。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch1_12a",
                "text": "0.07毫米。精确得像机器一样。你，合格了。欢迎加入火炮同好社。",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "workshop",
            },
            {
                "id": "ch1_13a",
                "text": "太好了！终于又有人加入了！我叫夏燃，是社团的炮手！",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "workshop",
            },
            {
                "id": "ch1_14a",
                "text": "我是温屿，负责弹道观测和气象测算。欢迎你。",
                "character": "wy",
                "char_name": "温屿",
                "characters": ["wy"],
                "bg": "workshop",
            },
            {
                "id": "ch1_15a",
                "text": "秋柚，后勤和装备维护。以后你的炮我帮你管！",
                "character": "qy",
                "char_name": "秋柚",
                "characters": ["qy"],
                "bg": "workshop",
            },
            {
                "id": "ch1_16a",
                "narrator": True,
                "text": "小G凝视着工作室内陈列的老旧火炮，眼神炽热如焰。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch1_17a",
                "text": "从今天起，我小G誓将此生奉献给火炮事业。我要让锋焰的火炮，响彻赛场！",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "workshop",
            },
            {
                "id": "ch1_end",
                "narrator": True,
                "text": "——就这样，火炮同好社的全员集结完毕。少年的赤心与古老的炮身共鸣，命运的齿轮开始转动。",
                "characters": [],
                "bg": "school",
                "chapter_end": True,
            },
        ],
    },
    # 第一章分支B：凭手感
    {
        "chapter": 1,
        "title": "第一章：入学逢炮，初心立誓",
        "scenes": [
            {
                "id": "ch1_11b",
                "narrator": True,
                "text": "小G随手一摸，报了个大致的数字。苏凛皱起眉头，重新用千分尺复核。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch1_12b",
                "text": "误差0.15毫米。还差得远。不过……你有胆量直接上手，至少不怕碰炮。留下来试试吧。",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "workshop",
            },
            {
                "id": "ch1_13b",
                "text": "没关系没关系！手感可以慢慢练的嘛！我是夏燃，社团的冲锋炮手！",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "workshop",
            },
            {
                "id": "ch1_14b",
                "text": "温屿。观测手。以后测量方面……我可以教你。",
                "character": "wy",
                "char_name": "温屿",
                "characters": ["wy"],
                "bg": "workshop",
            },
            {
                "id": "ch1_15b",
                "text": "我叫秋柚！装备我来管，别担心！",
                "character": "qy",
                "char_name": "秋柚",
                "characters": ["qy"],
                "bg": "workshop",
            },
            {
                "id": "ch1_16b",
                "narrator": True,
                "text": "尽管开局不够完美，小G依然望着那些火炮，眼中燃烧着坚定的火光。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch1_17b",
                "text": "我会用行动证明的。火炮——是我的信仰！",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "workshop",
            },
            {
                "id": "ch1_end",
                "narrator": True,
                "text": "——就这样，火炮同好社的全员集结完毕。少年的赤心与古老的炮身共鸣，命运的齿轮开始转动。",
                "characters": [],
                "bg": "school",
                "chapter_end": True,
            },
        ],
    },
    # ===== 第二章：队内磨合，炮阵成型 =====
    {
        "chapter": 2,
        "title": "第二章：队内磨合，炮阵成型",
        "scenes": [
            {
                "id": "ch2_1",
                "narrator": True,
                "text": "一周后。校内模拟赛场上，火炮同好社迎来了第一场校内演习赛。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch2_2",
                "text": "快！射速优先！趁他们还没架好炮，先打一波！",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "range",
            },
            {
                "id": "ch2_3",
                "text": "不行，炮架还没稳固，贸然开火精度会一塌糊涂。给我一分钟校准。",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "range",
            },
            {
                "id": "ch2_4",
                "text": "现在的风速是每秒12米，偏西26度。如果不等校准直接开炮，弹道会偏离至少8米。",
                "character": "wy",
                "char_name": "温屿",
                "characters": ["wy"],
                "bg": "range",
            },
            {
                "id": "ch2_5",
                "text": "弹链链接好了！但是炮架螺栓松了，给我30秒！",
                "character": "qy",
                "char_name": "秋柚",
                "characters": ["qy"],
                "bg": "range",
            },
            {
                "id": "ch2_6",
                "narrator": True,
                "text": "场面一片混乱——意见分歧导致射击迟迟无法执行，演习赛以惨败告终。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch2_7",
                "narrator": True,
                "text": "当晚，小G独自坐在昏暗的工作室里，盯着那门第一天加入时摸过的M101。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch2_8",
                "narrator": True,
                "text": "他拿起工具，开始拆解炮膛——从深夜到黎明，打磨、校准、擦拭，每一个部件都倾注心血。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch2_9",
                "narrator": True,
                "text": "天亮了。小G召集所有人来到靶场，将连夜调校好的火炮推上阵地。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch2_10",
                "text": "听我说——我们之所以失败，不是因为我们弱，是因为我们各自为战。观测先行、设计保障精度、炮手专注射击、后勤全程支援。这才是火炮战术的核心。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "range",
            },
            {
                "id": "ch2_11",
                "text": "温屿报参数，苏凛确认炮架，秋柚检查弹药，夏燃——你来开炮。按这个流程，再试一次。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "range",
            },
            {
                "id": "ch2_12",
                "text": "风向西北，风速6米，距离1200米，仰角34.7度！",
                "character": "wy",
                "char_name": "温屿",
                "characters": ["wy"],
                "bg": "range",
            },
            {
                "id": "ch2_13",
                "text": "炮架稳固，发射准备完毕！",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "range",
            },
            {
                "id": "ch2_14",
                "text": "弹药状态良好，全装药！",
                "character": "qy",
                "char_name": "秋柚",
                "characters": ["qy"],
                "bg": "range",
            },
            {
                "id": "ch2_15",
                "text": "了解！！开火——！！",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "range",
            },
            {
                "id": "ch2_16",
                "narrator": True,
                "text": "轰——！炮弹精准命中靶心。所有人都愣住了，然后不约而同地欢呼起来。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch2_17",
                "text": "成功了！！！我们成功了！！！",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "range",
            },
            {
                "id": "ch2_18",
                "narrator": True,
                "text": "从那一天起，四人炮阵的协同战术体系正式确立。小队不再是一盘散沙，而是真正凝聚成了一个整体。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch2_19",
                "narrator": True,
                "text": "深夜的工作室里，小G继续打磨着炮管。身后，四个女生不约而同地围了过来。",
                "characters": [],
                "bg": "workshop",
                "choices": [
                    {"text": "邀请苏凛一起研究炮架设计图纸", "next": "ch2_20a", "affection": {"sl": 3}},
                    {"text": "和夏燃去靶场试射新调校的火炮", "next": "ch2_20b", "affection": {"xr": 3}},
                    {"text": "向温屿请教弹道气象的计算方法", "next": "ch2_20c", "affection": {"wy": 3}},
                    {"text": "让秋柚帮忙一起整理维护装备", "next": "ch2_20d", "affection": {"qy": 3}},
                ],
            },
        ],
    },
    # 第二章各分支收敛到同样的结尾
    {
        "chapter": 2,
        "title": "第二章：队内磨合，炮阵成型",
        "scenes": [
            {
                "id": "ch2_20a",
                "narrator": True,
                "text": "苏凛和小G并肩坐在工作台前，对着炮架设计图争论到半夜。每一处结构的优化，都让两颗心靠得更近。",
                "characters": ["sl"],
                "bg": "workshop",
                "chapter_end": True,
            },
        ],
    },
    {
        "chapter": 2,
        "title": "第二章：队内磨合，炮阵成型",
        "scenes": [
            {
                "id": "ch2_20b",
                "narrator": True,
                "text": "月色下的靶场，夏燃操控着重新调校的火炮，每一发都正中靶心。她回头冲小G笑：「这炮，真棒！」",
                "characters": ["xr"],
                "bg": "range",
                "chapter_end": True,
            },
        ],
    },
    {
        "chapter": 2,
        "title": "第二章：队内磨合，炮阵成型",
        "scenes": [
            {
                "id": "ch2_20c",
                "narrator": True,
                "text": "温屿耐心地教小G推导弹道修正公式。两个人的头凑在一起，窗外星光洒落如银。",
                "characters": ["wy"],
                "bg": "workshop",
                "chapter_end": True,
            },
        ],
    },
    {
        "chapter": 2,
        "title": "第二章：队内磨合，炮阵成型",
        "scenes": [
            {
                "id": "ch2_20d",
                "narrator": True,
                "text": "秋柚一边擦拭炮架，一边絮絮叨叨地嘱咐小G：「不许再熬夜了，身体也是火炮手的武器啊。」",
                "characters": ["qy"],
                "bg": "workshop",
                "chapter_end": True,
            },
        ],
    },
    # ===== 第三章：地区联赛，初露锋芒 (简版) =====
    {
        "chapter": 3,
        "title": "第三章：地区联赛，初露锋芒",
        "scenes": [
            {
                "id": "ch3_1",
                "narrator": True,
                "text": "地区联赛的赛场。观众席上人声鼎沸，各大社团精英云集。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch3_2",
                "narrator": True,
                "text": "「火炮？那种笨重的老古董能打中什么？」轻武器社的选手轻蔑地笑着。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch3_3",
                "text": "别理他们。按我们的方式来。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "range",
            },
            {
                "id": "ch3_4",
                "narrator": True,
                "text": "比赛中，对手利用轻武器的高机动性快速压制阵地。小G冷静地重新布局炮阵。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch3_5",
                "text": "调整阵地到B7高地，仰角调到41度，利用远距优势反制他们的机动！",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "range",
            },
            {
                "id": "ch3_6",
                "narrator": True,
                "text": "在所有人惊讶的目光中，锋焰火炮社以精准的远距射击逆风翻盘，一战成名！",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch3_7",
                "narrator": True,
                "text": "赛后，全员在夕阳下的靶场庆祝。小G望着并肩作战的同伴们，心中充满力量。",
                "characters": [],
                "bg": "range",
                "choices": [
                    {"text": "和苏凛讨论下一门火炮的改良方案", "next": "ch3_8a", "affection": {"sl": 2}},
                    {"text": "陪夏燃加练快速架设炮架的技巧", "next": "ch3_8b", "affection": {"xr": 2}},
                    {"text": "跟温屿分析今天的弹道数据记录", "next": "ch3_8c", "affection": {"wy": 2}},
                    {"text": "帮秋柚检修今天损耗的炮架零件", "next": "ch3_8d", "affection": {"qy": 2}},
                ],
            },
        ],
    },
    {
        "chapter": 3,
        "title": "第三章：地区联赛，初露锋芒",
        "scenes": [
            {
                "id": "ch3_8a",
                "narrator": True,
                "text": "苏凛和小G拿着今天的射击数据，开始规划下一门火炮的设计参数。两人不约而同地画出了相似的炮架草图。",
                "characters": ["sl"],
                "bg": "workshop",
                "chapter_end": True,
            },
        ],
    },
    {
        "chapter": 3,
        "title": "第三章：地区联赛，初露锋芒",
        "scenes": [
            {
                "id": "ch3_8b",
                "narrator": True,
                "text": "「再来一次！」夏燃兴奋地喊道。她已经连续架设了二十次，每一次都比上一次更快。",
                "characters": ["xr"],
                "bg": "range",
                "chapter_end": True,
            },
        ],
    },
    {
        "chapter": 3,
        "title": "第三章：地区联赛，初露锋芒",
        "scenes": [
            {
                "id": "ch3_8c",
                "narrator": True,
                "text": "温屿翻开厚厚的观测记录本，上面密密麻麻记载着每一次射击的气象数据。",
                "characters": ["wy"],
                "bg": "workshop",
                "chapter_end": True,
            },
        ],
    },
    {
        "chapter": 3,
        "title": "第三章：地区联赛，初露锋芒",
        "scenes": [
            {
                "id": "ch3_8d",
                "narrator": True,
                "text": "秋柚熟练地拆下磨损的炮架垫片，换上新的。工具箱里井井有条，每一件都擦得锃亮。",
                "characters": ["qy"],
                "bg": "workshop",
                "chapter_end": True,
            },
        ],
    },
    # ===== 第四章：理念冲突 (简版) =====
    {
        "chapter": 4,
        "title": "第四章：理念冲突，信仰之争",
        "scenes": [
            {
                "id": "ch4_1",
                "narrator": True,
                "text": "全国大赛前夕，老牌强校「黑岩重工社」来访交流。",
                "characters": [],
                "bg": "school",
            },
            {
                "id": "ch4_2",
                "narrator": True,
                "text": "黑岩社的炮口径惊人，改装激进，追求极致火力输出。社长当众展示了一门可以连射的高压榴弹炮。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch4_3",
                "narrator": True,
                "text": "「这就是未来的趋势。你们那种老旧精工——早就该淘汰了。」",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch4_4",
                "narrator": True,
                "text": "队内出现了动摇的声音。有人开始质疑：我们是不是真的走错了路？",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch4_5",
                "text": "不。火炮从来不是单纯追求威力。它是精准、坚守、沉下心来铸就的信仰。我选择的路，我不会放弃。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "workshop",
            },
            {
                "id": "ch4_6",
                "narrator": True,
                "text": "小G独自进山进行了三天实地测试。风雨中调校炮具，每一个弹道数据都反复验证。",
                "characters": [],
                "bg": "range",
                "choices": [
                    {"text": "坚定精工路线，绝不妥协", "next": "ch4_7a", "affection": {"sl": 3}, "achievement": "献身"},
                    {"text": "尝试吸收黑岩的火力理念进行融合改良", "next": "ch4_7b", "affection": {"xr": 2}, "achievement": "创新"},
                ],
            },
        ],
    },
    {
        "chapter": 4,
        "title": "第四章：理念冲突，信仰之争",
        "scenes": [
            {
                "id": "ch4_7a",
                "narrator": True,
                "text": "小G回到社里，将测试数据摊开在所有人面前。每一个数字都证明着精工火炮的潜力。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch4_8a",
                "text": "精度0.03密位，散布半径不到2米——传统火炮能做到这个程度，我们还怕什么？",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "workshop",
            },
            {
                "id": "ch4_9a",
                "narrator": True,
                "text": "全员重新坚定了信念。黑岩的火力虽猛，但精工之路——才是锋焰火炮社的信仰。",
                "characters": [],
                "bg": "workshop",
                "chapter_end": True,
                "achievement": "献身",
            },
        ],
    },
    {
        "chapter": 4,
        "title": "第四章：理念冲突，信仰之争",
        "scenes": [
            {
                "id": "ch4_7b",
                "narrator": True,
                "text": "小G研究黑岩的设计思路后，提出折中方案：保留精工底子，在炮架结构上借鉴高压设计提升稳定性。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch4_8b",
                "text": "有意思！用高压结构提升耐久，但不放弃精度。这是一条新路！",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "workshop",
            },
            {
                "id": "ch4_9b",
                "narrator": True,
                "text": "融合路线让团队找到了新的方向——不拒绝学习对手的优点，也不放弃自己的核心信仰。",
                "characters": [],
                "bg": "workshop",
                "chapter_end": True,
                "achievement": "创新",
            },
        ],
    },
    # ===== 第五章：极致铸炮 (简版) =====
    {
        "chapter": 5,
        "title": "第五章：极致铸炮，热血备战全国赛",
        "scenes": [
            {
                "id": "ch5_1",
                "narrator": True,
                "text": "全国炽焰炮王大赛进入倒计时。校园里到处都是备战的身影。",
                "characters": [],
                "bg": "school",
            },
            {
                "id": "ch5_2",
                "narrator": True,
                "text": "小G和苏凛联手完成了新火炮「炽锋」的设计与打造——这是一门凝聚全团心血的专属竞技炮。",
                "characters": ["sl", "xg"],
                "bg": "workshop",
            },
            {
                "id": "ch5_3",
                "narrator": True,
                "text": "接着是地狱般的强化训练：千次弹道试射、极限环境调校、恶劣地形架设。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch5_4",
                "text": "山地阵地模拟——温屿，风向数据！",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "range",
            },
            {
                "id": "ch5_5",
                "text": "东南风，阵风18米，仰角需补偿2.3度！",
                "character": "wy",
                "char_name": "温屿",
                "characters": ["wy"],
                "bg": "range",
            },
            {
                "id": "ch5_6",
                "text": "炮架调整完毕，适应15度斜坡！",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "range",
            },
            {
                "id": "ch5_7",
                "text": "弹药防潮检查完成，可以发射！",
                "character": "qy",
                "char_name": "秋柚",
                "characters": ["qy"],
                "bg": "range",
            },
            {
                "id": "ch5_8",
                "text": "收到！！炽锋——发射！！",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "range",
            },
            {
                "id": "ch5_9",
                "narrator": True,
                "text": "夕阳西下，五人坐在靶场的高地上，眺望着被晚霞染红的阵地。青春与炮声交织，热血在每一个人的心中澎湃。",
                "characters": ["sl", "xr", "wy", "qy", "xg"],
                "bg": "range",
                "chapter_end": True,
            },
        ],
    },
    # ===== 第六章：全国大赛 (简版) =====
    {
        "chapter": 6,
        "title": "第六章：全国大赛，炽焰对决",
        "scenes": [
            {
                "id": "ch6_1",
                "narrator": True,
                "text": "全国炽焰炮王大赛——正式开赛！各路顶尖火炮强队齐聚全国大赛会场。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch6_2",
                "narrator": True,
                "text": "精准射靶、阵地攻防、改装创意、编队协同——四大赛事轮番上演。锋焰火炮社一路高歌猛进。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch6_3",
                "narrator": True,
                "text": "最终决赛——直面宿敌黑岩重工社。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch6_4",
                "narrator": True,
                "text": "决赛战场条件极其恶劣：强风14级、复杂起伏地形、靶标800度高速移动。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch6_5",
                "narrator": True,
                "text": "黑岩全力爆发超高火力强行压制，锋焰的阵地不断受到冲击。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch6_6",
                "text": "全体稳住！！温屿，立即更新风偏数据！苏凛，调整仰角补偿！秋柚，确认最后一发弹药！",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "range",
            },
            {
                "id": "ch6_7",
                "text": "风速修正+3.7度，距离1850米，全要素弹道参数已锁定！",
                "character": "wy",
                "char_name": "温屿",
                "characters": ["wy"],
                "bg": "range",
            },
            {
                "id": "ch6_8",
                "text": "炮架仰角39.2度，补偿完毕，稳定性100%！",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "range",
            },
            {
                "id": "ch6_9",
                "text": "弹药整备完成！这就是最后一发了——炽锋，交给你了！",
                "character": "qy",
                "char_name": "秋柚",
                "characters": ["qy"],
                "bg": "range",
            },
            {
                "id": "ch6_10",
                "text": "全员就绪！！炽锋——终极一炮——发射！！",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "range",
            },
            {
                "id": "ch6_11",
                "narrator": True,
                "text": "轰——！！！",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch6_12",
                "narrator": True,
                "text": "在狂风中，炮弹划出一道完美的弧线，以零误差命中高速移动靶标的中心。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch6_13",
                "narrator": True,
                "text": "全场寂静了一秒，然后爆发出雷鸣般的掌声。",
                "characters": [],
                "bg": "range",
                "chapter_end": True,
            },
        ],
    },
    # ===== 第七章：炮鸣终章 (简版) =====
    {
        "chapter": 7,
        "title": "第七章：炮鸣终章，献身赤心",
        "scenes": [
            {
                "id": "ch7_1",
                "narrator": True,
                "text": "全国总冠军——锋焰高等学园火炮同好社！",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch7_2",
                "narrator": True,
                "text": "炮鸣声回荡在整座会场。五个人紧紧拥抱在一起，泪水和笑容交织。",
                "characters": ["sl", "xr", "wy", "qy", "xg"],
                "bg": "range",
            },
            {
                "id": "ch7_3",
                "narrator": True,
                "text": "黑岩社长走到小G面前，伸出手。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch7_4",
                "narrator": True,
                "text": "「我承认了。你们的路——是对的。精工与信仰，才是一切的根基。」",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch7_5",
                "narrator": True,
                "text": "两只手紧紧握住。曾经的宿敌，此刻惺惺相惜。",
                "characters": [],
                "bg": "range",
            },
            {
                "id": "ch7_6",
                "narrator": True,
                "text": "小G抬头望向天空。一路走来，从废弃社团到全国之巅——这条路，他走得无悔。",
                "characters": [],
                "bg": "school",
                "choices": [
                    {"text": "立志走入专业军械领域，一生献身火炮研发", "next": "ch7_end_main", "affection": {}, "achievement": "献身"},
                    {"text": "牵起最珍视之人的手，走向共同的未来", "next": "ch7_end_love", "affection": {}, "achievement": "团结"},
                ],
            },
        ],
    },
    # 主线热血结局
    {
        "chapter": 7,
        "title": "终章：主线热血结局",
        "scenes": [
            {
                "id": "ch7_end_main",
                "narrator": True,
                "text": "小G并未止步于冠军。他选择了进入专业军械研究领域，将青春与理想全数奉献给热爱的火炮事业。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ch7_end_main_2",
                "narrator": True,
                "text": "多年后，新一代「炽焰」系列火炮列装全国各校，成为新一代火炮少年的梦想开端。",
                "characters": [],
                "bg": "school",
            },
            {
                "id": "ch7_end_main_3",
                "narrator": True,
                "text": "小G站在研究中心的落地窗前，望着远方靶场升起的炮烟，嘴角浮起微笑。",
                "characters": ["xg"],
                "bg": "range",
            },
            {
                "id": "ch7_end_main_4",
                "text": "火炮——是我一生的信仰。这条路，我还会继续走下去。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "range",
            },
            {
                "id": "ending",
                "narrator": True,
                "text": "——全剧终——\n感谢游玩《炽焰炮阵：铸锋少年》！",
                "characters": [],
                "bg": "school",
                "chapter_end": True,
                "final_ending": True,
            },
        ],
    },
    # 恋爱结局（根据最高好感度女主）
    {
        "chapter": 7,
        "title": "终章：恋爱结局",
        "scenes": [
            {
                "id": "ch7_end_love",
                "narrator": True,
                "text": "小G转过身，望向一直以来陪伴在自己身边的那个人。所有的炮声、硝烟、汗水——都不及此刻她眼中的光芒。",
                "characters": [],
                "bg": "school",
            },
            {
                "id": "ch7_end_love_2",
                "narrator": True,
                "text": "「谢谢你，一直在。」\n「谢什么，我们不是一直在一起吗？」",
                "characters": [],
                "bg": "school",
            },
            {
                "id": "ch7_end_love_3",
                "narrator": True,
                "text": "从今往后，一人铸炮，一人相伴。青春与热爱，双向奔赴。",
                "characters": [],
                "bg": "school",
            },
            {
                "id": "ch7_end_love_4",
                "narrator": True,
                "text": "社团的传承也在继续——新的少年少女们推开了火炮同好社的门，就像当年的他们一样。",
                "characters": [],
                "bg": "workshop",
            },
            {
                "id": "ending",
                "narrator": True,
                "text": "——全剧终——\n感谢游玩《炽焰炮阵：铸锋少年》！",
                "characters": [],
                "bg": "school",
                "chapter_end": True,
                "final_ending": True,
            },
        ],
    },
]


# ============================================================
# 剧情扩展：补足单线约 10 分钟游玩体量
# ============================================================

STORY_EXPANSIONS_AFTER: Dict[str, List[dict]] = {
    "ch1_1": [
        {
            "id": "ch1_1_ext_1",
            "narrator": True,
            "text": "清晨的锋焰高等学园像一座沉睡的兵工厂。教学楼墙面嵌着退役炮闩，操场边陈列着历届冠军队留下的炮架，连风吹过旗杆的声音都带着金属的颤音。",
            "characters": [],
            "bg": "school",
        },
        {
            "id": "ch1_1_ext_2",
            "narrator": True,
            "text": "小G站在校门口，背包里只装了三样东西：一本翻旧的《内弹道基础》、一把父亲留下的测径规，以及一张写着「我要造出最强火炮」的便签。",
            "characters": [],
            "bg": "school",
        },
    ],
    "ch1_2": [
        {
            "id": "ch1_2_ext_1",
            "narrator": True,
            "text": "机甲社的招新台前排着长队，轻武器社用电子靶打出漂亮的连发成绩。相比之下，火炮社的方向安静得近乎冷清，像一条被时代遗忘的小路。",
            "characters": [],
            "bg": "school",
        },
        {
            "id": "ch1_2_ext_2",
            "text": "火炮不是过时的东西。它只是太沉、太慢、太需要耐心，所以才显得不合群。",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "school",
        },
    ],
    "ch1_5": [
        {
            "id": "ch1_5_ext_1",
            "narrator": True,
            "text": "工作室比想象中更旧。墙角堆着被拆开的驻退机，白板上写满初速、膛压、散布圆和修正量。这里没有豪华设备，却有一种让人不敢随便呼吸的认真。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch1_5_ext_2",
            "narrator": True,
            "text": "那门老式榴弹炮的炮盾被擦得很亮，像一块沉默的奖牌。小G一眼就看出它被无数次拆装、修复、再试射，磨痕里藏着一支弱小社团不肯认输的历史。",
            "characters": [],
            "bg": "workshop",
        },
    ],
    "ch1_9": [
        {
            "id": "ch1_9_ext_1",
            "text": "别急着回答。火炮不会因为你热血就变准，金属也不会因为你喊口号就少磨损。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "workshop",
        },
        {
            "id": "ch1_9_ext_2",
            "narrator": True,
            "text": "苏凛说话时没有提高音量，却让整个工作室都安静下来。夏燃停下擦炮弹模型的手，温屿合上记录本，秋柚抱着工具箱探出半个身子。",
            "characters": [],
            "bg": "workshop",
        },
    ],
    "ch1_12a": [
        {
            "id": "ch1_12a_ext_1",
            "text": "我不是想当机器。我只是觉得，如果误差能少一点，炮弹就能更接近我们真正想抵达的地方。",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "workshop",
        },
        {
            "id": "ch1_12a_ext_2",
            "text": "这句话不错。记住它，等你第一次被赛场风偏打脸的时候，再拿出来看看。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "workshop",
        },
    ],
    "ch1_12b": [
        {
            "id": "ch1_12b_ext_1",
            "text": "我知道自己太轻率了。可我不想离开，哪怕从最基础的清洁、搬运、抄数据开始也可以。",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "workshop",
        },
        {
            "id": "ch1_12b_ext_2",
            "text": "火炮社不缺会逞强的人，缺的是愿意承认误差、再把误差一点点磨掉的人。明天六点，别迟到。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "workshop",
        },
    ],
    "ch2_1": [
        {
            "id": "ch2_1_ext_1",
            "narrator": True,
            "text": "第二天六点，靶场的草叶还挂着露水。远处风向袋懒洋洋地垂着，像在嘲笑这群新生居然相信努力能追上经验。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch2_1_ext_2",
            "text": "先跑三圈，再搬炮架。炮手的手臂不只是为了扣扳机，也是为了把失误扛回来。",
            "character": "xr",
            "char_name": "夏燃",
            "characters": ["xr"],
            "bg": "range",
        },
    ],
    "ch2_4": [
        {
            "id": "ch2_4_ext_1",
            "narrator": True,
            "text": "第一轮装填训练只进行了二十分钟，小G的手套就被磨破了。炮闩的重量、弹药箱的边角、炮架锁扣的反冲，每一个细节都在提醒他：热爱不是想象中的轻盈。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch2_4_ext_2",
            "text": "别只盯着炮口。看脚下，看锁销，看你的队友什么时候需要你让出半步。",
            "character": "qy",
            "char_name": "秋柚",
            "characters": ["qy"],
            "bg": "range",
        },
    ],
    "ch2_9": [
        {
            "id": "ch2_9_ext_1",
            "narrator": True,
            "text": "温屿把气象记录摊开，纸面上密密麻麻地写着温度、湿度、侧风和气压。小G第一次意识到，所谓命中目标，并不是瞄准后开火那么简单。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch2_9_ext_2",
            "text": "弹道像人的选择。你以为自己走的是直线，其实一路都被看不见的风推着。",
            "character": "wy",
            "char_name": "温屿",
            "characters": ["wy"],
            "bg": "range",
        },
    ],
    "ch2_13": [
        {
            "id": "ch2_13_ext_1",
            "narrator": True,
            "text": "训练结束后，苏凛没有立刻宣布成绩。她把每个人的错误写在白板上，又把每个错误后面可能造成的后果补齐：偏靶、卡壳、超压、结构疲劳。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch2_13_ext_2",
            "text": "我们不是为了漂亮地开一炮而训练。我们是为了在最糟糕的情况下，也能让下一炮可信。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "workshop",
        },
    ],
    "ch2_18": [
        {
            "id": "ch2_18_ext_1",
            "narrator": True,
            "text": "夜里，小G一个人回到工作室，把白天所有弹着点重新画在坐标纸上。散布圆像一团不肯听话的火，他盯着它，直到眼睛发酸。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch2_18_ext_2",
            "text": "如果把驻锄角度再压低一点，后坐位移也许能减少。可那样会不会影响下一次复位？",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "workshop",
        },
    ],
    "ch2_20a": [
        {
            "id": "ch2_20a_ext_1",
            "text": "你看这里，炮架不是越硬越好。该让它吸收的力，就别推给炮身。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "workshop",
        },
        {
            "id": "ch2_20a_ext_2",
            "narrator": True,
            "text": "两人一直算到窗外天色发蓝。小G发现苏凛严厉的背后不是冷漠，而是害怕任何一次粗心毁掉大家共同守住的火光。",
            "characters": [],
            "bg": "workshop",
        },
    ],
    "ch2_20b": [
        {
            "id": "ch2_20b_ext_1",
            "text": "再来一次！别怕炮声，炮声越大，越说明它在回应你！",
            "character": "xr",
            "char_name": "夏燃",
            "characters": ["xr"],
            "bg": "range",
        },
        {
            "id": "ch2_20b_ext_2",
            "narrator": True,
            "text": "夏燃的热情像火，却不是盲目的火。她每次冲在最前，也最先检查安全线、炮尾和耳罩。小G从她身上学会了勇敢的边界。",
            "characters": [],
            "bg": "range",
        },
    ],
    "ch2_20c": [
        {
            "id": "ch2_20c_ext_1",
            "text": "别讨厌公式。公式不是用来束缚炮弹的，是用来告诉我们它为什么会自由。",
            "character": "wy",
            "char_name": "温屿",
            "characters": ["wy"],
            "bg": "range",
        },
        {
            "id": "ch2_20c_ext_2",
            "narrator": True,
            "text": "温屿把风速修正讲得很慢。小G听着听着，忽然觉得那些枯燥的数字像一张温柔的网，把不可预测的天空一点点托住。",
            "characters": [],
            "bg": "range",
        },
    ],
    "ch2_20d": [
        {
            "id": "ch2_20d_ext_1",
            "text": "装备维护最像照顾人。哪里发热，哪里松动，哪里只是逞强不说，都要看得出来。",
            "character": "qy",
            "char_name": "秋柚",
            "characters": ["qy"],
            "bg": "workshop",
        },
        {
            "id": "ch2_20d_ext_2",
            "narrator": True,
            "text": "秋柚把零件按顺序铺开，像整理一份只属于火炮的病历。小G第一次觉得，后勤不是幕后，而是所有炮声能够响起的前提。",
            "characters": [],
            "bg": "workshop",
        },
    ],
    "ch3_1": [
        {
            "id": "ch3_1_ext_1",
            "narrator": True,
            "text": "地区联赛的报名确认书贴在公告栏上，纸面被无数双手摸得微微发皱。小G在名单末尾看到「火炮同好社」五个字，心脏忽然重重跳了一下。",
            "characters": [],
            "bg": "school",
        },
        {
            "id": "ch3_1_ext_2",
            "text": "上了赛场就没人会因为我们设备旧而让分。旧炮要赢，就只能比新炮更懂自己。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "school",
        },
    ],
    "ch3_3": [
        {
            "id": "ch3_3_ext_1",
            "narrator": True,
            "text": "第一支对手队伍带来了崭新的电子火控系统，观测屏亮得刺眼。火炮同好社这边只有旧测距镜、手写弹道表和一群紧张到沉默的少年少女。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch3_3_ext_2",
            "text": "别看他们的屏幕，看我们的靶。只要弹着点还在纸上，胜负就还在炮口前。",
            "character": "xr",
            "char_name": "夏燃",
            "characters": ["xr"],
            "bg": "range",
        },
    ],
    "ch3_5": [
        {
            "id": "ch3_5_ext_1",
            "narrator": True,
            "text": "第一发偏右。第二发压低。第三发虽然进了有效区，却离中心还有一段刺眼的距离。观众席传来窃窃私语，小G握着记录板，指节泛白。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch3_5_ext_2",
            "text": "风向变了两度，湿度比开赛前高。把修正量给我，我相信你们。",
            "character": "wy",
            "char_name": "温屿",
            "characters": ["wy"],
            "bg": "range",
        },
    ],
    "ch3_7": [
        {
            "id": "ch3_7_ext_1",
            "narrator": True,
            "text": "当最后一发命中靶心边缘时，夏燃的欢呼几乎盖过了裁判哨声。苏凛只是低头看了一眼炮架位移，嘴角却终于松开。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch3_7_ext_2",
            "text": "我们赢的不是他们，是昨天那个还不知道怎么配合的自己。",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "range",
        },
    ],
    "ch3_8a": [
        {
            "id": "ch3_8a_ext_1",
            "narrator": True,
            "text": "苏凛把胜利后的第一张图纸推给小G。纸上没有庆祝，只有红笔圈出的缺陷：炮架横摆、锁止迟滞、复位不稳。",
            "characters": [],
            "bg": "workshop",
        },
    ],
    "ch3_8b": [
        {
            "id": "ch3_8b_ext_1",
            "narrator": True,
            "text": "夏燃把加练安排在夕阳最刺眼的时候。她说真正的赛场不会等你状态最好才开始，炮手必须学会在心跳和汗水里找准节奏。",
            "characters": [],
            "bg": "range",
        },
    ],
    "ch3_8c": [
        {
            "id": "ch3_8c_ext_1",
            "narrator": True,
            "text": "温屿带着小G复盘每一次修正。那些看似冷静的数字背后，其实藏着她在赛前反复观测到深夜的耐心。",
            "characters": [],
            "bg": "range",
        },
    ],
    "ch3_8d": [
        {
            "id": "ch3_8d_ext_1",
            "narrator": True,
            "text": "秋柚拆下被震松的连接件，发现里面有一道细小裂纹。她没有责怪任何人，只是把它放进证物袋，像收起一枚差点发生的失败。",
            "characters": [],
            "bg": "workshop",
        },
    ],
    "ch4_1": [
        {
            "id": "ch4_1_ext_1",
            "narrator": True,
            "text": "黑岩工高的车队开进校园时，几乎所有人都停下脚步。被黑布盖住的新式火炮轮廓锋利，像一头趴在拖车上的钢铁猛兽。",
            "characters": [],
            "bg": "school",
        },
        {
            "id": "ch4_1_ext_2",
            "narrator": True,
            "text": "他们的队长只看了火炮同好社一眼，便移开视线。那不是轻蔑，更像是已经把胜负写进公式后的无须确认。",
            "characters": [],
            "bg": "school",
        },
    ],
    "ch4_3": [
        {
            "id": "ch4_3_ext_1",
            "text": "极限火力不是错，但如果每一发都在透支炮身，我们赢下来的到底是比赛，还是一次昂贵的燃尽？",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "workshop",
        },
        {
            "id": "ch4_3_ext_2",
            "text": "可如果连火力都不敢追求，我们又凭什么说自己热爱火炮？",
            "character": "xr",
            "char_name": "夏燃",
            "characters": ["xr"],
            "bg": "workshop",
        },
    ],
    "ch4_5": [
        {
            "id": "ch4_5_ext_1",
            "narrator": True,
            "text": "争论持续到深夜。温屿的计算结果显示融合方案并非不可能，秋柚却指出现有材料承受不了连续高压。每个人都对，却没有一个答案足够完整。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch4_5_ext_2",
            "text": "也许火炮真正难的地方，不是把一种理念推到极限，而是在极限前承认别人也看见了真理的一部分。",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "workshop",
        },
    ],
    "ch4_8a": [
        {
            "id": "ch4_8a_ext_1",
            "narrator": True,
            "text": "坚持精工路线后，小G连续三天守在车床旁。每一次切削都慢得让人焦躁，可当炮闩滑入闭锁槽的瞬间，所有人都听见了近乎完美的咔哒声。",
            "characters": [],
            "bg": "workshop",
        },
    ],
    "ch4_8b": [
        {
            "id": "ch4_8b_ext_1",
            "narrator": True,
            "text": "融合火力理念后，工作室像被点燃。夏燃负责实射节奏，苏凛负责结构底线，温屿反推弹道窗口，秋柚把每一次异常温升都贴上警示签。",
            "characters": [],
            "bg": "workshop",
        },
    ],
    "ch5_1": [
        {
            "id": "ch5_1_ext_1",
            "narrator": True,
            "text": "全国赛资格确认的那天，工作室没有欢呼太久。桌面上很快铺满更大的图纸、更复杂的材料清单，以及一份几乎没有休息日的备战表。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch5_1_ext_2",
            "text": "从今天起，我们不再只是弱小社团。我们是锋焰的代表，任何一次敷衍都会被全国赛场放大。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "workshop",
        },
    ],
    "ch5_3": [
        {
            "id": "ch5_3_ext_1",
            "narrator": True,
            "text": "新炮的代号定为「炽锋」。它还只是一串参数和几根粗糙的型材，却已经让每个人在经过图纸时放轻脚步，像怕惊醒一个尚未成形的梦。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch5_3_ext_2",
            "text": "炽锋要有足够高的初速，也要能承受连续射击。它不能只是漂亮，它得活到最后一轮。",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "workshop",
        },
    ],
    "ch5_5": [
        {
            "id": "ch5_5_ext_1",
            "narrator": True,
            "text": "第一次整炮装配失败在凌晨两点。锁止机构偏差不到一毫米，却足以让所有努力停在最后一步。夏燃气得想踢工具箱，被秋柚一把拦住。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch5_5_ext_2",
            "text": "别踢它，它也很努力了。我们把它拆开，再让它以正确的样子回来。",
            "character": "qy",
            "char_name": "秋柚",
            "characters": ["qy"],
            "bg": "workshop",
        },
    ],
    "ch5_7": [
        {
            "id": "ch5_7_ext_1",
            "narrator": True,
            "text": "试射前一晚，小G梦见炮弹离膛后在空中停住。所有公式、汗水和期待都悬在那一点上，直到远处有人喊他的名字。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch5_7_ext_2",
            "text": "你怕失败吗？",
            "character": "wy",
            "char_name": "温屿",
            "characters": ["wy"],
            "bg": "workshop",
        },
        {
            "id": "ch5_7_ext_3",
            "text": "怕。但比起失败，我更怕有一天我不敢再把炮口指向更远的地方。",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "workshop",
        },
    ],
    "ch5_8": [
        {
            "id": "ch5_8_ext_1",
            "narrator": True,
            "text": "炽锋的第一发试射震得靶场边的安全旗猛地扬起。烟尘散开后，所有人都冲向观测屏，连苏凛都忘了保持平时的冷静。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch5_8_ext_2",
            "narrator": True,
            "text": "弹着点不是完美中心，却稳定、干净、可重复。对真正的炮手来说，这比偶然的靶心更珍贵，因为它意味着下一步仍然掌握在自己手里。",
            "characters": [],
            "bg": "range",
        },
    ],
    "ch6_1": [
        {
            "id": "ch6_1_ext_1",
            "narrator": True,
            "text": "全国赛场的看台高得像山。各校队伍推着自己的火炮从通道里走出，履带、轮架、炮盾和队旗在灯光下连成一条耀眼的钢铁河流。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch6_1_ext_2",
            "text": "深呼吸。我们不是来参观冠军的，我们是来把自己的名字打进靶纸里的。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "range",
        },
    ],
    "ch6_3": [
        {
            "id": "ch6_3_ext_1",
            "narrator": True,
            "text": "预赛第一轮，炽锋的复位速度引起了裁判注意。小G听见邻队低声议论「旧社团怎么可能做出这种结构」，心里却没有得意，只有更深的紧张。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch6_3_ext_2",
            "text": "别被夸奖打乱节奏。炮弹不会因为别人惊讶就自动进靶心。",
            "character": "wy",
            "char_name": "温屿",
            "characters": ["wy"],
            "bg": "range",
        },
    ],
    "ch6_5": [
        {
            "id": "ch6_5_ext_1",
            "narrator": True,
            "text": "半决赛开始前，炽锋的炮架传来一声不该有的轻响。秋柚立刻趴下检查，手电光在缝隙里一寸寸移动，所有人的呼吸都跟着压低。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch6_5_ext_2",
            "text": "不是断裂，是锁止片磨出了毛刺。给我三分钟，我能处理。",
            "character": "qy",
            "char_name": "秋柚",
            "characters": ["qy"],
            "bg": "range",
        },
    ],
    "ch6_7": [
        {
            "id": "ch6_7_ext_1",
            "narrator": True,
            "text": "黑岩工高的火炮终于揭开炮衣。它比地区赛时更激进，炮口制退器像张开的獠牙，整门炮散发着把一切问题都交给火力解决的气势。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch6_7_ext_2",
            "text": "他们把炮做成了冲锋。那我们就把炮做成阵地。谁能站到最后，谁就有资格谈理念。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "range",
        },
    ],
    "ch6_9": [
        {
            "id": "ch6_9_ext_1",
            "narrator": True,
            "text": "决赛第三轮，侧风突然增强。观众席发出一阵骚动，黑岩选择提高装药量硬压弹道，而锋焰这边却陷入短暂沉默。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch6_9_ext_2",
            "text": "不能硬追。风不是敌人，是条件。我们顺着它修正，不和它赌气。",
            "character": "wy",
            "char_name": "温屿",
            "characters": ["wy"],
            "bg": "range",
        },
    ],
    "ch6_11": [
        {
            "id": "ch6_11_ext_1",
            "narrator": True,
            "text": "最后一发装填前，夏燃的手停在炮闩旁。她平时最吵，此刻却安静得像整座靶场只剩下她和那门炮。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch6_11_ext_2",
            "text": "炽锋，拜托了。把我们这一路的声音，全都带过去。",
            "character": "xr",
            "char_name": "夏燃",
            "characters": ["xr"],
            "bg": "range",
        },
    ],
    "ch6_13": [
        {
            "id": "ch6_13_ext_1",
            "narrator": True,
            "text": "靶心确认的灯亮起时，小G没有立刻欢呼。他先看向苏凛，看向夏燃、温屿、秋柚，看向那门被他们一点点从旧梦里推出来的炽锋。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch6_13_ext_2",
            "narrator": True,
            "text": "掌声像海浪一样涌来。可小G心里最清楚，真正震耳欲聋的不是观众席，而是无数个深夜里他们没有放弃的声音。",
            "characters": [],
            "bg": "range",
        },
    ],
    "ch7_1": [
        {
            "id": "ch7_1_ext_1",
            "narrator": True,
            "text": "夺冠后的锋焰校园热闹得像节日。可当小G独自走进工作室时，里面还是熟悉的机油味、白板和那张被反复修改到卷边的炮架图。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch7_1_ext_2",
            "text": "赢了以后，梦想会变轻吗？",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "workshop",
        },
        {
            "id": "ch7_1_ext_3",
            "narrator": True,
            "text": "没有人回答。墙上的旧榴弹炮静静立着，像在告诉他：胜利只是一次命中，而人生还有更远的靶。",
            "characters": [],
            "bg": "workshop",
        },
    ],
    "ch7_3": [
        {
            "id": "ch7_3_ext_1",
            "narrator": True,
            "text": "毕业意向表发下来时，大家第一次认真谈起未来。苏凛想进军械研究所，夏燃想成为实弹测试炮手，温屿被气象弹道实验室邀请，秋柚则想开一间装备维护工坊。",
            "characters": [],
            "bg": "school",
        },
        {
            "id": "ch7_3_ext_2",
            "text": "原来我们不是要永远待在同一个工作室，而是要把这里教给我们的东西带到更远的地方。",
            "character": "xg",
            "char_name": "小G",
            "characters": ["xg"],
            "bg": "school",
        },
    ],
    "ch7_5": [
        {
            "id": "ch7_5_ext_1",
            "narrator": True,
            "text": "最后一次社团活动，他们没有训练，只是把所有工具擦干净，把炽锋的参数备份三遍，再把旧炮盾上的划痕一个个摸过去。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch7_5_ext_2",
            "text": "以后不管走到哪里，只要听见炮声，我大概都会想起这里。",
            "character": "qy",
            "char_name": "秋柚",
            "characters": ["qy"],
            "bg": "workshop",
        },
    ],
    "ch7_end_main_2": [
        {
            "id": "ch7_end_main_2_ext_1",
            "narrator": True,
            "text": "多年后，小G第一次以研究员身份站上试验场。新型火炮的炮身比炽锋更长、更冷峻，可他检查炮闩时，动作仍像当年在旧工作室里那样小心。",
            "characters": [],
            "bg": "range",
        },
        {
            "id": "ch7_end_main_2_ext_2",
            "narrator": True,
            "text": "他把第一份测试报告寄回锋焰，信封里夹着一张便签：火炮不是一个人的浪漫，是一群人把误差磨到极限后的信任。",
            "characters": [],
            "bg": "school",
        },
    ],
    "ch7_end_love_2": [
        {
            "id": "ch7_end_love_2_ext_1",
            "narrator": True,
            "text": "告白没有发生在烟花下，而是在工作室熄灯前。桌上还有没收完的扳手和弹道纸，窗外远处传来晚训的炮声，像替他们轻轻敲了一下门。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch7_end_love_2_ext_2",
            "narrator": True,
            "text": "那个人没有立刻回答，只是把小G衣袖上的铁屑拍掉。这个动作太熟悉了，熟悉到他们忽然明白，很多陪伴早就在语言之前完成了选择。",
            "characters": [],
            "bg": "workshop",
        },
    ],
}

STORY_LONGFORM_EXPANSIONS_AFTER: Dict[str, List[dict]] = {
    "ch1_3": [
        {
            "id": "ch1_3_long_1",
            "narrator": True,
            "text": "这句话小G没有说给任何人听。他只是把它压在心里，像把一枚还没有装填的炮弹压进弹药箱。来锋焰之前，很多人劝他选更热门的机甲方向，只有他知道自己真正想追逐的是炮口后那套严密而炽热的世界。",
            "characters": [],
            "bg": "school",
        }
    ],
    "ch1_4": [
        {
            "id": "ch1_4_long_1",
            "narrator": True,
            "text": "旧楼的走廊很窄，墙上贴着褪色的安全守则和几张被雨水泡皱的比赛海报。海报角落里，火炮同好社曾经的成绩只停在地区赛八强，小G却觉得那行小字比任何冠军横幅都更像邀请。",
            "characters": [],
            "bg": "school",
        }
    ],
    "ch1_8": [
        {
            "id": "ch1_8_long_1",
            "narrator": True,
            "text": "游标卡尺很旧，刻线却被保养得极清楚。小G握住它时，忽然意识到这不是一道入社题，而是一种提问：你究竟愿不愿意把热血落到毫米、角分和每一次重复确认里。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch2_2": [
        {
            "id": "ch2_2_long_1",
            "narrator": True,
            "text": "团队训练不像个人练习。一个人快了会撞乱节奏，一个人慢了会拖住整门炮。小G以前总以为技术足够好就能解决问题，现在才发现火炮首先考验的是人与人之间能否同步。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch2_6": [
        {
            "id": "ch2_6_long_1",
            "text": "小G，你的眼睛一直在找炮口，可你的手还没记住炮尾。真正的炮手闭着眼也知道哪里危险。",
            "character": "qy",
            "char_name": "秋柚",
            "characters": ["qy"],
            "bg": "range",
        },
        {
            "id": "ch2_6_long_2",
            "narrator": True,
            "text": "秋柚的话听起来温和，却让小G背后一凉。他低头重新检查炮尾安全区，第一次把「喜欢火炮」和「敬畏火炮」放在了同一个位置。",
            "characters": [],
            "bg": "range",
        },
    ],
    "ch2_11": [
        {
            "id": "ch2_11_long_1",
            "narrator": True,
            "text": "中午休息时，大家围坐在炮架阴影下吃便当。夏燃把炸鸡分给所有人，温屿边吃边记录风速，苏凛看似在休息，手指却还在无意识地推演复位结构。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch2_16": [
        {
            "id": "ch2_16_long_1",
            "narrator": True,
            "text": "傍晚的工作室只剩台灯亮着。小G在清点工具时发现，每一件东西都有固定位置，连最小的垫片都贴着编号。混乱可以靠热情撑一时，秩序才能让热情走得更远。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch2_19": [
        {
            "id": "ch2_19_long_1",
            "narrator": True,
            "text": "那天结束前，苏凛让小G把训练日志读出来。听见自己笨拙的记录被队友补充、修正、接住，他突然明白，所谓社团不是一群人站在一起，而是一群人愿意替彼此补上盲区。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch3_2": [
        {
            "id": "ch3_2_long_1",
            "narrator": True,
            "text": "赛前检录时，其他学校的队员不断投来好奇的目光。炽锋还未诞生，火炮同好社推来的仍是那门被修补过无数次的旧炮，但它的炮身擦得发亮，像不肯被时间判负。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch3_4": [
        {
            "id": "ch3_4_long_1",
            "text": "别把紧张藏起来。紧张说明你知道这一炮很重要。把它变成检查清单，而不是变成手抖。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "range",
        }
    ],
    "ch3_6": [
        {
            "id": "ch3_6_long_1",
            "narrator": True,
            "text": "逆转并不是突然发生的。它来自温屿多算出的半度修正，来自秋柚提前拧紧的锁销，来自夏燃在炮声里没有乱掉的呼吸，也来自小G终于学会把自己的判断交给队伍。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch4_2": [
        {
            "id": "ch4_2_long_1",
            "narrator": True,
            "text": "黑岩的训练方式像一场压迫感十足的演示。高装药、快节奏、极限射角，每一个动作都在宣告他们相信火力能碾过一切犹豫。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch4_4": [
        {
            "id": "ch4_4_long_1",
            "text": "我不是反对热血。我只是见过太多把热血当借口的人，最后让炮替他们的鲁莽付出代价。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "workshop",
        },
        {
            "id": "ch4_4_long_2",
            "text": "那就让我证明，火力不是鲁莽。真正的火力，是明知道风险还把它控制住以后，依然敢扣下扳机。",
            "character": "xr",
            "char_name": "夏燃",
            "characters": ["xr"],
            "bg": "workshop",
        },
    ],
    "ch4_6": [
        {
            "id": "ch4_6_long_1",
            "narrator": True,
            "text": "小G看着两份方案，觉得它们像两条不同的弹道。一条稳健，落点可靠；一条炽烈，射程惊人。而他必须决定，火炮同好社究竟要用哪种声音回应黑岩。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch5_2": [
        {
            "id": "ch5_2_long_1",
            "narrator": True,
            "text": "炽锋的设计会议从早开到晚。苏凛负责结构底线，夏燃负责射击节奏，温屿负责弹道窗口，秋柚负责维护可行性。小G坐在中间，像站在四条火线交汇处。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch5_4": [
        {
            "id": "ch5_4_long_1",
            "narrator": True,
            "text": "经费不足的问题比任何对手都现实。能买新材料的地方不多，能省的地方却每一处都关系安全。秋柚把预算表算到小数点后两位，最后默默划掉了自己的新工具申请。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch5_6": [
        {
            "id": "ch5_6_long_1",
            "text": "我来当第一轮试射炮手。不是因为我不怕，是因为我最清楚它什么时候像真的准备好了。",
            "character": "xr",
            "char_name": "夏燃",
            "characters": ["xr"],
            "bg": "range",
        }
    ],
    "ch5_9": [
        {
            "id": "ch5_9_long_1",
            "narrator": True,
            "text": "试射成功后，没有人急着离开。大家坐在靶场边，看夕阳一点点落到炮身上。炽锋的金属轮廓被染成橙红色，像终于拥有了自己的名字。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch6_2": [
        {
            "id": "ch6_2_long_1",
            "narrator": True,
            "text": "开幕式上，主持人念到锋焰高等学园时，掌声并不算最热烈。小G却听见身后有人喊火炮同好社的名字，那声音不大，却足够让他挺直背脊。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch6_4": [
        {
            "id": "ch6_4_long_1",
            "narrator": True,
            "text": "每一轮比赛之间，炽锋都要被完整检查。炮身温度、锁止磨损、驻退复位、炮架螺栓，秋柚的记录板翻得飞快，像一台温柔又严苛的安全系统。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch6_6": [
        {
            "id": "ch6_6_long_1",
            "narrator": True,
            "text": "半决赛最后阶段，炽锋连续三发落点稳定，观众席终于爆发出真正属于锋焰的欢呼。小G却把目光落在炮尾，因为他知道下一轮才是黑岩等待他们的地方。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch6_8": [
        {
            "id": "ch6_8_long_1",
            "text": "他们会用第一发压住气势。我们不用抢声量，我们抢稳定。",
            "character": "sl",
            "char_name": "苏凛",
            "characters": ["sl"],
            "bg": "range",
        },
        {
            "id": "ch6_8_long_2",
            "text": "那最后一发让我来。稳定也可以很热血，对吧？",
            "character": "xr",
            "char_name": "夏燃",
            "characters": ["xr"],
            "bg": "range",
        },
    ],
    "ch6_10": [
        {
            "id": "ch6_10_long_1",
            "narrator": True,
            "text": "比分交替上升，像两条互不相让的弹道在空中缠斗。黑岩每一次命中都带着压倒性的声势，锋焰每一次回应却都更靠近中心。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch6_12": [
        {
            "id": "ch6_12_long_1",
            "narrator": True,
            "text": "最后一发飞行的时间其实很短，可在小G眼里，它像穿过了整个学年：入社测试、第一次偏靶、深夜争论、失败装配、全国赛的灯光，全都被那条弧线串了起来。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch7_2": [
        {
            "id": "ch7_2_long_1",
            "narrator": True,
            "text": "庆功会那天，夏燃把蛋糕切得歪歪扭扭，温屿认真给每个人拍照，秋柚坚持让大家先洗手再碰奖杯，苏凛站在一旁嫌弃他们吵，却没有离开半步。",
            "characters": [],
            "bg": "school",
        }
    ],
    "ch7_4": [
        {
            "id": "ch7_4_long_1",
            "narrator": True,
            "text": "小G把自己的意向表写了又划，划了又写。军械研究、试验场、社团传承、共同未来，每一个选择都不是离开过去，而是决定如何继续回应过去。",
            "characters": [],
            "bg": "school",
        }
    ],
    "ch7_6": [
        {
            "id": "ch7_6_long_1",
            "narrator": True,
            "text": "最后，他把笔放下。窗外传来新生训练的第一声炮响，不够稳，也不够准，却像极了当初推开旧楼大门时的自己。",
            "characters": [],
            "bg": "school",
        }
    ],
}

STORY_FINAL_LENGTH_EXPANSIONS_AFTER: Dict[str, List[dict]] = {
    "ch1_16a": [
        {
            "id": "ch1_16a_final_len_1",
            "narrator": True,
            "text": "社团登记表被推到小G面前时，他迟疑了一秒。签下名字很简单，真正沉重的是从此以后，所有训练、失败、争吵与胜利都会和这间旧工作室绑在一起。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch1_16b": [
        {
            "id": "ch1_16b_final_len_1",
            "narrator": True,
            "text": "社团登记表被推到小G面前时，他迟疑了一秒。签下名字很简单，真正沉重的是从此以后，所有训练、失败、争吵与胜利都会和这间旧工作室绑在一起。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch2_8": [
        {
            "id": "ch2_8_final_len_1",
            "narrator": True,
            "text": "小G开始学会在炮声之外听见更多声音：锁销到位的轻响、炮架受力后的细微呻吟、队友换气时的节奏。这些声音很小，却比欢呼更早告诉他一门炮是否值得信任。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch2_12": [
        {
            "id": "ch2_12_final_len_1",
            "narrator": True,
            "text": "训练日志的最后一栏写着「今日误差原因」。小G原本只想填技术问题，后来又补上了犹豫、抢拍、沟通太慢。火炮把所有人的弱点都放大，却也给了他们修正弱点的坐标。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch3_4": [
        {
            "id": "ch3_4_final_len_1",
            "narrator": True,
            "text": "裁判举旗前，时间像被拉长。小G看见夏燃压低重心，苏凛确认闭锁，温屿盯着风向袋，秋柚的手停在备用工具旁。那一刻，他知道自己不是一个人在瞄准。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch4_6": [
        {
            "id": "ch4_6_final_len_1",
            "narrator": True,
            "text": "选择之前，小G走到旧榴弹炮旁，把掌心贴在冰冷炮盾上。它不会说话，却像把前辈们留下的所有失败都借给他，让他明白理念不是口号，而是愿意承担后果的方向。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch5_4": [
        {
            "id": "ch5_4_final_len_1",
            "narrator": True,
            "text": "为了省下一组高强度连接件，大家轮流去旧仓库拆可用零件。灰尘呛得人直咳嗽，可每找到一枚还能使用的螺栓，工作室里就像多了一点继续向前的资本。",
            "characters": [],
            "bg": "workshop",
        }
    ],
    "ch5_6": [
        {
            "id": "ch5_6_final_len_1",
            "narrator": True,
            "text": "试射清单被贴在炮盾内侧，一项项划掉时，紧张没有减少，反而变得更清晰。小G忽然喜欢上这种清晰，因为它说明害怕已经不再只是害怕，而是可以被执行的步骤。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch6_8": [
        {
            "id": "ch6_8_final_len_1",
            "narrator": True,
            "text": "黑岩第一发命中后，全场瞬间沸腾。小G没有回头看计分牌，他只是把下一发修正量写得更稳。越是在声浪里，越要让自己的笔画像炮架一样沉住。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch6_10": [
        {
            "id": "ch6_10_final_len_1",
            "narrator": True,
            "text": "对手的强大并没有击垮他们，反而把每个人训练时留下的痕迹逼了出来。夏燃的果断、温屿的冷静、秋柚的细致、苏凛的底线，在这一刻像齿轮一样咬合。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch6_12": [
        {
            "id": "ch6_12_final_len_1",
            "narrator": True,
            "text": "炮弹落下之前，没有人敢提前庆祝。所有人都只是站在原地，像把自己这一年的重量也一并交给了那条弧线。直到靶场灯光亮起，他们才终于敢呼吸。",
            "characters": [],
            "bg": "range",
        }
    ],
    "ch7_4": [
        {
            "id": "ch7_4_final_len_1",
            "narrator": True,
            "text": "他终于明白，所谓献身火炮事业，并不是把人生变成一根笔直的炮管。那更像一条长长的弹道，会经过同伴、爱、离别和传承，最后仍然朝着热爱的方向落下。",
            "characters": [],
            "bg": "school",
        }
    ],
    "ch7_5": [
        {
            "id": "ch7_5_final_len_1",
            "narrator": True,
            "text": "离开前，小G把自己的第一张测量便签夹进社团日志。纸边已经卷起，上面的字也不算漂亮，但那是他第一次把梦想从口号写成数字的证据。",
            "characters": [],
            "bg": "workshop",
        },
        {
            "id": "ch7_5_final_len_2",
            "narrator": True,
            "text": "他没有把便签放在最显眼的位置，只是夹在一页普通训练记录后面。因为他希望后来者翻到它时会明白，伟大的炮声往往开始于一个人愿意认真读数的瞬间。",
            "characters": [],
            "bg": "workshop",
        }
    ],
}

STORY_BRANCHING_AFTER: Dict[str, dict] = {
    "ch2_15": {
        "choices": [
            {"text": "复盘装填节奏，优先减少队内失误", "next": "ch2_15_branch_rhythm", "affection": {"xr": 1}, "achievement": "唯实"},
            {"text": "检查炮架材料，优先排除结构隐患", "next": "ch2_15_branch_frame", "affection": {"sl": 1}, "achievement": "俭朴"},
            {"text": "重算风偏表，优先提高弹道预测", "next": "ch2_15_branch_weather", "affection": {"wy": 1}},
        ],
        "scenes": [
            {
                "id": "ch2_15_branch_rhythm",
                "text": "小G把训练录像倒回十几遍，和夏燃一起数每一次装填、闭锁、退步的节拍。她笑着说这比跑圈还累，可下一轮训练里，整支队伍的动作第一次像一门真正的炮。",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "range",
                "next": "ch2_16",
            },
            {
                "id": "ch2_15_branch_frame",
                "text": "小G没有急着追求更漂亮的成绩，而是和苏凛把旧炮架拆到只剩主梁。两人发现几处可修补的疲劳点，用最省钱的方式换来了更可靠的复位。",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "workshop",
                "next": "ch2_16",
            },
            {
                "id": "ch2_15_branch_weather",
                "text": "小G坐到温屿身边，把风偏表从头重算。那些数字起初像雾，后来渐渐变成清晰的路标，指向每一发炮弹可能抵达的位置。",
                "character": "wy",
                "char_name": "温屿",
                "characters": ["wy"],
                "bg": "range",
                "next": "ch2_16",
            },
        ],
    },
    "ch5_4": {
        "choices": [
            {"text": "坚持采购关键新件，压缩非核心开销", "next": "ch5_4_branch_newpart", "affection": {"sl": 1}},
            {"text": "从旧仓库翻修可用零件，贯彻俭朴路线", "next": "ch5_4_branch_reuse", "affection": {"qy": 2}, "achievement": "俭朴"},
            {"text": "申请靶场勤务换取材料赞助", "next": "ch5_4_branch_sponsor", "affection": {"xr": 1}},
        ],
        "scenes": [
            {
                "id": "ch5_4_branch_newpart",
                "text": "小G划掉了几项外观改装，把预算集中到闭锁机构的新件上。苏凛看着清单点了点头：漂亮可以以后再说，安全和精度不能等。",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "workshop",
                "next": "ch5_5",
            },
            {
                "id": "ch5_4_branch_reuse",
                "text": "秋柚带着小G钻进旧仓库，从报废器材里挑出还能修复的零件。灰尘落满肩膀时，她却笑得很开心：省下来的每一枚螺栓，都会变成炽锋的一部分。",
                "character": "qy",
                "char_name": "秋柚",
                "characters": ["qy"],
                "bg": "workshop",
                "next": "ch5_5",
            },
            {
                "id": "ch5_4_branch_sponsor",
                "text": "夏燃拉着小G去靶场帮忙维护设备，用一整天的勤务换来材料赞助。回程时两人累得说不出话，却都觉得那袋合金件重得很值得。",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "range",
                "next": "ch5_5",
            },
        ],
    },
    "ch6_8": {
        "choices": [
            {"text": "稳住节奏，按苏凛方案打稳定散布", "next": "ch6_8_branch_stable", "affection": {"sl": 1}, "achievement": "唯实"},
            {"text": "抓住窗口，给夏燃一次高风险反击", "next": "ch6_8_branch_fire", "affection": {"xr": 2}, "achievement": "创新"},
            {"text": "相信温屿，等待下一阵侧风回落", "next": "ch6_8_branch_wait", "affection": {"wy": 2}},
        ],
        "scenes": [
            {
                "id": "ch6_8_branch_stable",
                "text": "小G选择把节奏压稳。炽锋没有打出最惊人的炮声，却连续两发落在几乎相同的位置，像用沉默告诉黑岩：稳定本身也是一种压迫。",
                "character": "sl",
                "char_name": "苏凛",
                "characters": ["sl"],
                "bg": "range",
                "next": "ch6_9",
            },
            {
                "id": "ch6_8_branch_fire",
                "text": "夏燃得到许可的瞬间，眼睛亮得像炮口焰。那一发带着更激进的装填节奏冲向靶心边缘，虽然风险很高，却把全场气势重新拉回锋焰这边。",
                "character": "xr",
                "char_name": "夏燃",
                "characters": ["xr"],
                "bg": "range",
                "next": "ch6_9",
            },
            {
                "id": "ch6_8_branch_wait",
                "text": "小G顶住观众席的催促，选择等待。十几秒后风向袋微微回摆，温屿报出新的修正量。炮弹离膛时，他知道这份耐心没有白费。",
                "character": "wy",
                "char_name": "温屿",
                "characters": ["wy"],
                "bg": "range",
                "next": "ch6_9",
            },
        ],
    },
    "ch7_4": {
        "choices": [
            {"text": "选择军械研究所，继续追逐更远射程", "next": "ch7_4_branch_research", "affection": {"sl": 1}, "achievement": "献身"},
            {"text": "留下整理社团资料，帮助后来者起步", "next": "ch7_4_branch_legacy", "affection": {"qy": 1}, "achievement": "团结"},
            {"text": "先去靶场，再认真听自己心里的答案", "next": "ch7_4_branch_range", "affection": {"wy": 1}},
        ],
        "scenes": [
            {
                "id": "ch7_4_branch_research",
                "text": "小G把研究所的志愿填在第一栏。那不是离开伙伴，而是带着他们教会自己的精度、勇气、耐心和维护意识，去面对更复杂的火炮问题。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "school",
                "next": "ch7_5",
            },
            {
                "id": "ch7_4_branch_legacy",
                "text": "小G决定先把社团资料整理完整。图纸、弹道表、维护记录、失败报告，全都被他分门别类放好。他希望后来者少走一点弯路，却仍然保留犯错后重新站起的勇气。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "workshop",
                "next": "ch7_5",
            },
            {
                "id": "ch7_4_branch_range",
                "text": "小G没有立刻填表，而是去了靶场。风从空旷地带吹来，带着熟悉的尘土味。他忽然明白，自己并不是没有答案，只是想郑重地向这片场地告别。",
                "character": "xg",
                "char_name": "小G",
                "characters": ["xg"],
                "bg": "range",
                "next": "ch7_5",
            },
        ],
    },
}


def _apply_story_expansions() -> None:
    """把扩展剧情插入到原有脚本中，保持原分支跳转稳定。"""
    targeted_scene_ids = {
        choice.get("next")
        for group in STORY_SCRIPT
        for scene in group.get("scenes", [])
        for choice in scene.get("choices", [])
    }
    seen_scene_ids: Dict[str, int] = {}
    for group in STORY_SCRIPT:
        expanded_scenes: List[dict] = []
        for scene in group.get("scenes", []):
            terminal_flags = {
                key: scene.pop(key)
                for key in ("chapter_end", "final_ending")
                if key in scene
            }
            branch = STORY_BRANCHING_AFTER.get(scene.get("id", ""))
            if branch:
                scene["choices"] = branch["choices"]
            expanded_scenes.append(scene)
            inserted_scenes = [
                *STORY_EXPANSIONS_AFTER.get(scene.get("id", ""), []),
                *STORY_LONGFORM_EXPANSIONS_AFTER.get(scene.get("id", ""), []),
                *STORY_FINAL_LENGTH_EXPANSIONS_AFTER.get(scene.get("id", ""), []),
                *([] if not branch else branch["scenes"]),
            ]
            expanded_scenes.extend(inserted_scenes)
            if terminal_flags:
                expanded_scenes[-1].update(terminal_flags)
        for scene in expanded_scenes:
            scene_id = scene.get("id", "")
            if not scene_id:
                continue
            count = seen_scene_ids.get(scene_id, 0)
            seen_scene_ids[scene_id] = count + 1
            if count and scene_id not in targeted_scene_ids:
                scene["id"] = f"{scene_id}_{count + 1}"
        group["scenes"] = expanded_scenes


_apply_story_expansions()

# ============================================================
# 游戏状态管理
# ============================================================


class GameState:
    """全局游戏状态"""

    def __init__(self) -> None:
        self.current_scene_index: int = 0
        self.current_chapter_group: int = 0
        self.affection: Dict[str, int] = {"sl": 0, "xr": 0, "wy": 0, "qy": 0}
        self.achievements: List[str] = []
        self.scene_history: List[str] = []
        self.chapter_start_indices: Dict[int, int] = {}
        self._scan_chapters()

    def _scan_chapters(self) -> None:
        """扫描剧情数据，记录每个章节第一个场景组的起始索引"""
        for i, group in enumerate(STORY_SCRIPT):
            ch = group["chapter"]
            if ch not in self.chapter_start_indices:
                self.chapter_start_indices[ch] = i

    def apply_affection(self, aff: Dict[str, int]) -> None:
        """应用好感度变化"""
        for char, delta in aff.items():
            if char in self.affection:
                self.affection[char] += delta

    def add_achievement(self, ach: str) -> None:
        """添加成就"""
        if ach and ach not in self.achievements:
            self.achievements.append(ach)

    def get_titles(self) -> List[str]:
        """根据最终成就组合计算隐藏称号。"""
        achievements = set(self.achievements)
        if achievements == {"团结", "献身", "求是", "创新"}:
            return ["光荣的炮兵"]
        if achievements == {"团结", "俭朴", "唯实", "创新"}:
            return ["航奸"]
        if achievements == {"团结", "献身", "求是", "创新", "俭朴", "唯实"}:
            return ["双生一体"]
        return []

    def get_top_heroine(self) -> Optional[str]:
        """获取好感度最高的女主"""
        if not any(self.affection.values()):
            return None
        return max(self.affection, key=self.affection.get)  # type: ignore[arg-type]

    def get_heroine_name(self, char_id: str) -> str:
        """将 char_id 转为中文名"""
        name_map = {"sl": "苏凛", "xr": "夏燃", "wy": "温屿", "qy": "秋柚"}
        return name_map.get(char_id, char_id)

    def to_dict(self) -> dict:
        return {
            "current_scene_index": self.current_scene_index,
            "current_chapter_group": self.current_chapter_group,
            "affection": dict(self.affection),
            "achievements": list(self.achievements),
            "scene_history": list(self.scene_history),
        }

    def from_dict(self, data: dict) -> None:
        self.current_scene_index = data.get("current_scene_index", 0)
        self.current_chapter_group = data.get("current_chapter_group", 0)
        self.affection = data.get("affection", {"sl": 0, "xr": 0, "wy": 0, "qy": 0})
        self.achievements = data.get("achievements", [])
        self.scene_history = data.get("scene_history", [])

    def save(self) -> None:
        """保存游戏存档"""
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self) -> bool:
        """加载游戏存档，返回是否成功"""
        if not SAVE_FILE.exists():
            return False
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.from_dict(data)
            return True
        except (json.JSONDecodeError, KeyError):
            return False


# ============================================================
# TUI 画面定义
# ============================================================


class TitleScreen(Screen):
    """标题画面"""

    BINDINGS = [
        Binding("enter", "start_game", "开始游戏"),
        Binding("l", "load_game", "读取存档"),
        Binding("m", "show_menu", "设置"),
        Binding("c", "show_credits", "Credits"),
        Binding("q", "quit", "退出游戏"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Label("RaiChi-Soft", id="title_company"),
                Label("", id="title_logo"),
                Static("", id="title_text"),
                Static("", id="title_sub"),
                Static("", id="title_disclaimer"),
                Static("", id="title_menu"),
                id="title_inner",
            ),
            id="title_container",
        )
        yield Footer()

    def on_mount(self) -> None:
        title_company = self.query_one("#title_company", Label)
        title_company.update(
            Text("RaiChi-Soft", style=Style(color="bright_magenta", bold=True))
        )
        title_logo = self.query_one("#title_logo", Label)
        title_logo.update(
            "\n"
            "█████╗  ██████╗ ████████╗██╗   ██╗ ██████╗  █████╗  ██╗     \n"
            "██╔══██╗██╔══██╗╚══██╔══╝╚██╗ ██╔╝██╔════╝ ██╔══██╗ ██║     \n"
            "███████║██████╔╝   ██║    ╚████╔╝ ██║  ███╗███████║ ██║     \n"
            "██╔══██║██╔══██╗   ██║     ╚██╔╝  ██║   ██║██╔══██║ ██║     \n"
            "██║  ██║██║  ██║   ██║      ██║   ╚██████╔╝██║  ██║ ███████╗\n"
            "╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝      ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚══════╝\n"
        )
        title_text = self.query_one("#title_text", Static)
        title_text.update(
            Text(
                "⚒ 炽焰炮阵：铸锋少年 ⚒",
                style=Style(color="bright_yellow", bold=True),
            )
        )
        title_sub = self.query_one("#title_sub", Static)
        title_sub.update(Text("以炮为魂·以火为志", style=Style(color="grey70", italic=True)))
        title_disclaimer = self.query_one("#title_disclaimer", Static)
        title_disclaimer.update(
            Text(DISCLAIMER_TEXT, style=Style(color="bright_green"))
        )
        title_menu = self.query_one("#title_menu", Static)
        title_menu.update(
            Text(
                "[ Enter ] 开始新游戏\n"
                "[  L   ] 读取存档\n"
                "[  M   ] 设置\n"
                "[  C   ] Credits\n"
                "[  Q   ] 退出游戏",
                style=Style(color="grey54"),
            )
        )

    def action_start_game(self) -> None:
        game_state = GameState()
        self.app.game_state = game_state
        self.app.push_screen(MainGameScreen())

    def action_load_game(self) -> None:
        gs = GameState()
        if gs.load():
            gs._scan_chapters()
            self.app.game_state = gs
            self.app.push_screen(MainGameScreen(restore_index=gs.current_chapter_group))
        else:
            self.app.push_screen(
                MessageScreen("没有找到存档文件。\n请先开始新游戏。", title="提示")
            )

    def action_quit(self) -> None:
        self.app.exit()

    def action_show_menu(self) -> None:
        self.app.push_screen(SettingsScreen())

    def action_show_credits(self) -> None:
        self.app.push_screen(CreditsScreen())


class MessageScreen(ModalScreen):
    """通用消息弹窗"""

    def __init__(self, message: str, dismiss_callback=None, title: str = "系统") -> None:
        super().__init__()
        self.message = message
        self.dismiss_callback = dismiss_callback
        self.screen_title = title

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Label(f"── {self.screen_title} ──", id="msg_title"),
                Static(Text(self.message, style=Style(color="white")), id="msg_body"),
                Button("确定", variant="primary", id="msg_ok"),
                id="msg_inner",
            ),
            id="msg_overlay",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "msg_ok":
            self.dismiss()
            if self.dismiss_callback:
                self.dismiss_callback()


class SaveLoadScreen(ModalScreen):
    """存档/读档确认画面"""

    def __init__(self, game_state: "GameState", is_save: bool = True) -> None:
        super().__init__()
        self.game_state = game_state
        self.is_save = is_save

    def compose(self) -> ComposeResult:
        action = "保存" if self.is_save else "读取"
        yield Container(
            Vertical(
                Label(f"── {action}存档 ──", id="sl_title"),
                Static("", id="sl_info"),
                Horizontal(
                    Button("确认", variant="primary", id="sl_confirm"),
                    Button("取消", variant="default", id="sl_cancel"),
                    id="sl_buttons",
                ),
                id="sl_inner",
            ),
            id="msg_overlay",
        )

    def on_mount(self) -> None:
        info = self.query_one("#sl_info", Static)
        if self.is_save:
            info.update(
                Text(
                    f"将当前进度保存到存档文件。\n"
                    f"当前章节：可在主界面查看",
                    style=Style(color="white"),
                )
            )
        else:
            info.update(
                Text(
                    "读取存档将覆盖当前游戏进度。\n确定要读取存档吗？",
                    style=Style(color="bright_yellow"),
                )
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "sl_confirm":
            if self.is_save:
                self.game_state.save()
                self.dismiss()
                self.app.push_screen(MessageScreen("存档成功！"))
            else:
                new_gs = GameState()
                if new_gs.load():
                    new_gs._scan_chapters()
                    self.app.game_state = new_gs
                    self.dismiss()
                    self.app.pop_screen()
                    self.app.push_screen(
                        MainGameScreen(restore_index=new_gs.current_chapter_group)
                    )
                else:
                    self.dismiss()
                    self.app.push_screen(
                        MessageScreen("读取存档失败。")
                    )
        elif event.button.id == "sl_cancel":
            self.dismiss()


class SettingsScreen(ModalScreen):
    """设置页"""

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Label("── Settings ──", id="settings_title"),
                Static("", id="settings_info"),
                Horizontal(
                    Button("Music On/Off", variant="primary", id="music_toggle"),
                    Button("Vol -", id="music_down"),
                    Button("Vol +", id="music_up"),
                    id="settings_buttons",
                ),
                Button("Close", variant="default", id="settings_close"),
                id="settings_inner",
            ),
            id="msg_overlay",
        )

    def on_mount(self) -> None:
        self._refresh_info()

    def _refresh_info(self) -> None:
        audio = getattr(self.app, "audio", None)
        music_status = "On" if audio and audio.enabled else "Off"
        volume = audio.volume if audio else 0
        info = (
            f"Music: {music_status}    Volume: {volume}%\n\n"
            "Use the buttons below to control background music.\n"
            "Open Credits from the title screen with [C], or in game with [C]."
        )
        self.query_one("#settings_info", Static).update(
            Text(info, style=Style(color="white"))
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        audio = getattr(self.app, "audio", None)
        if event.button.id == "music_toggle" and audio:
            audio.toggle()
            self._refresh_info()
        elif event.button.id == "music_down" and audio:
            audio.volume_down()
            self._refresh_info()
        elif event.button.id == "music_up" and audio:
            audio.volume_up()
            self._refresh_info()
        elif event.button.id == "settings_close":
            self.dismiss()


class CreditsScreen(ModalScreen):
    """工作人员与致谢页"""

    def compose(self) -> ComposeResult:
        credits = (
            "Planning: RaiChi-Soft\n"
            "Original Work: Doubao\n"
            "Scenario: CodeX\n"
            "Music: Gemini\n"
            "Art: Gemin\n\n"
            "Special Thanks:\n"
            "ConcernedApe, Actas, Production IMS, Yuzu-Soft, Sphere\n\n"
            f"{DISCLAIMER_TEXT}"
        )
        yield Container(
            Vertical(
                Label("── Credits ──", id="credits_title"),
                Static(Text(credits, style=Style(color="white")), id="credits_info"),
                Button("Close", variant="primary", id="credits_close"),
                id="credits_inner",
            ),
            id="msg_overlay",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "credits_close":
            self.dismiss()


class MainGameScreen(Screen):
    """主游戏画面"""

    BINDINGS = [
        Binding("enter", "advance", "继续"),
        Binding("1", "choice_0", "选项1", key_display="1"),
        Binding("2", "choice_1", "选项2", key_display="2"),
        Binding("3", "choice_2", "选项3", key_display="3"),
        Binding("4", "choice_3", "选项4", key_display="4"),
        Binding("s", "save_game", "存档"),
        Binding("l", "load_game", "读档"),
        Binding("a", "show_affection", "好感度"),
        Binding("m", "show_menu", "菜单"),
        Binding("c", "show_credits", "Credits"),
        Binding("r", "return_title", "返回标题"),
    ]

    current_group_index = reactive(0)
    current_scene_index = reactive(0)
    showing_choices = reactive(False)

    def __init__(self, restore_index: int = 0) -> None:
        super().__init__()
        self._restore_index = restore_index

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="game_container"):
            with Horizontal(id="game_area"):
                # 左侧：角色立绘区域
                with Container(id="char_panel"):
                    yield Static("", id="char_art")
                # 右侧：文字区域
                with Vertical(id="text_panel"):
                    yield Static("", id="chapter_label")
                    yield Static("", id="char_name_label")
                    yield Static("", id="dialog_text")
                    # 选项按钮区域
                    with Vertical(id="choices_container"):
                        yield Button("", id="choice_btn_0", classes="choice-btn")
                        yield Button("", id="choice_btn_1", classes="choice-btn")
                        yield Button("", id="choice_btn_2", classes="choice-btn")
                        yield Button("", id="choice_btn_3", classes="choice-btn")
        yield Footer()

    def on_mount(self) -> None:
        self.current_group_index = self._restore_index
        self.current_scene_index = 0
        if hasattr(self.app, "game_state"):
            gs = self.app.game_state
            if self._restore_index == gs.current_chapter_group:
                self.current_scene_index = gs.current_scene_index
        try:
            self._render_scene()
        except Exception:
            # DOM 未就绪，延迟一帧后重试
            self._check_dom_ready()

    def _check_dom_ready(self) -> None:
        """检查 DOM 是否就绪，就绪则渲染"""
        if self._query_safe("#dialog_text", Static) is not None:
            self._render_scene()
        else:
            self.set_timer(0.1, self._check_dom_ready)

    def _get_current_group(self) -> dict:
        """获取当前场景组"""
        gs = self.app.game_state
        idx = self.current_group_index
        if idx >= len(STORY_SCRIPT):
            return STORY_SCRIPT[-1]  # 安全回退
        return STORY_SCRIPT[idx]

    def _get_current_scene(self) -> Optional[dict]:
        group = self._get_current_group()
        scenes = group.get("scenes", [])
        idx = self.current_scene_index
        if idx < len(scenes):
            return scenes[idx]
        return None

    def _find_next_chapter_group_index(self) -> int:
        """返回下一个更高章节的场景组，避免同章不同分支串线。"""
        current_chapter = self._get_current_group().get("chapter", 0)
        for idx in range(self.current_group_index + 1, len(STORY_SCRIPT)):
            if STORY_SCRIPT[idx].get("chapter", 0) > current_chapter:
                return idx
        return len(STORY_SCRIPT)

    def _jump_to_scene_id(self, scene_id: str) -> bool:
        """跳转到指定场景 ID。"""
        for gi, group in enumerate(STORY_SCRIPT):
            for si, scene in enumerate(group.get("scenes", [])):
                if scene.get("id") == scene_id:
                    self.current_group_index = gi
                    self.current_scene_index = si
                    return True
        return False

    def _query_safe(self, selector: str, widget_class):
        """安全查询 widget，不存在则返回 None"""
        results = self.query(selector)
        if results:
            return results.first(widget_class)
        return None

    def _render_scene(self) -> None:
        """渲染当前场景"""
        scene = self._get_current_scene()
        if scene is None:
            self._end_of_content()
            return

        gs = self.app.game_state

        # 记录场景ID
        scene_id = scene.get("id", "")
        if scene_id and scene_id not in gs.scene_history:
            gs.scene_history.append(scene_id)

        # 更新章节标题
        group = self._get_current_group()
        ch_label = self._query_safe("#chapter_label", Static)
        if ch_label:
            ch_label.update(
                Text(group.get("title", ""), style=Style(color="bright_cyan", bold=True))
            )

        # 更新角色名
        name_label = self._query_safe("#char_name_label", Static)
        if name_label:
            if scene.get("narrator"):
                name_label.update(Text("── 旁白 ──", style=Style(color="grey70", italic=True)))
            else:
                char_name = scene.get("char_name", "")
                name_label.update(
                    Text(
                        f"▎ {char_name}",
                        style=Style(color="bright_green", bold=True),
                    )
                )

        # 更新对话文本
        dialog = self._query_safe("#dialog_text", Static)
        if dialog:
            text = scene.get("text", "")
            dialog.update(Text(text, style=Style(color="white")))

        # 更新左侧图像：有人物时显示角色立绘，否则显示对应场景图
        char_art = self._query_safe("#char_art", Static)
        if char_art:
            characters = scene.get("characters", [])
            if characters:
                arts = []
                for index, cid in enumerate(characters):
                    if index:
                        arts.append(Text("\n"))
                    art = get_character_art(cid)
                    arts.append(art)
                    name = CHARACTER_MAP.get(cid, cid)
                    arts.append(Text(f"\n  {name}\n", style=Style(color="grey70")))
                if arts:
                    combined = Text.assemble(*arts)
                    char_art.update(combined)
                else:
                    char_art.update(Text(""))
            else:
                bg_id = scene.get("bg", "")
                scene_art = get_scene_art(bg_id) if bg_id else Text("")
                if scene_art.plain:
                    scene_name = {
                        "school": "锋焰高等学园",
                        "workshop": "火炮同好社",
                        "range": "训练靶场",
                    }.get(bg_id, bg_id)
                    char_art.update(
                        Text.assemble(
                            scene_art,
                            Text(f"\n  {scene_name}", style=Style(color="grey70")),
                        )
                    )
                else:
                    char_art.update(Text(""))

        # 处理选项
        choices_container = self._query_safe("#choices_container", Vertical)
        choices = scene.get("choices", [])
        if choices and choices_container:
            self.showing_choices = True
            choices_container.display = True
            for i in range(4):
                btn = self._query_safe(f"#choice_btn_{i}", Button)
                if btn:
                    if i < len(choices):
                        btn.label = f"[{i+1}] {choices[i]['text']}"
                        btn.display = True
                        btn.disabled = False
                    else:
                        btn.label = ""
                        btn.display = False
                        btn.disabled = True
        elif choices_container:
            self.showing_choices = False
            choices_container.display = False
            for i in range(4):
                btn = self._query_safe(f"#choice_btn_{i}", Button)
                if btn:
                    btn.disabled = True

        # 更新游戏状态
        gs.current_chapter_group = self.current_group_index
        gs.current_scene_index = self.current_scene_index

    def _advance_scene(self) -> None:
        """进入下一场景"""
        scene = self._get_current_scene()
        if scene is None:
            return

        gs = self.app.game_state

        # 应用当前场景的成就
        if scene.get("achievement"):
            gs.add_achievement(scene["achievement"])

        # 检查是否是最终结局
        if scene.get("final_ending"):
            self._show_ending()
            return

        # 分支短线结束后跳回公共主线
        if scene.get("next"):
            if self._jump_to_scene_id(scene["next"]):
                gs.current_chapter_group = self.current_group_index
                gs.current_scene_index = self.current_scene_index
                self._render_scene()
            return

        # 检查是否是章节结束
        if scene.get("chapter_end"):
            self.current_group_index = self._find_next_chapter_group_index()
            self.current_scene_index = 0
            gs.current_chapter_group = self.current_group_index
            gs.current_scene_index = 0
            self._render_scene()
            return

        # 如果没有选项，直接前进
        if not scene.get("choices"):
            self.current_scene_index += 1
            gs.current_scene_index = self.current_scene_index
            self._render_scene()
            return

    def _handle_choice(self, choice_index: int) -> None:
        """处理玩家选择"""
        scene = self._get_current_scene()
        if scene is None:
            return

        choices = scene.get("choices", [])
        if choice_index >= len(choices):
            return

        choice = choices[choice_index]
        gs = self.app.game_state

        # 应用好感度
        gs.apply_affection(choice.get("affection", {}))

        # 应用成就
        if choice.get("achievement"):
            gs.add_achievement(choice["achievement"])

        # 查找下一个场景
        found = self._jump_to_scene_id(choice["next"])

        if not found:
            # 回退：前进一个场景
            self.current_scene_index += 1

        gs.current_chapter_group = self.current_group_index
        gs.current_scene_index = self.current_scene_index
        self.showing_choices = False
        self._render_scene()

    def _end_of_content(self) -> None:
        """内容结束"""
        ch_label = self._query_safe("#chapter_label", Static)
        if ch_label:
            ch_label.update(Text("── 终剧 ──", style=Style(color="bright_red", bold=True)))
        name_label = self._query_safe("#char_name_label", Static)
        if name_label:
            name_label.update(Text(""))
        dialog = self._query_safe("#dialog_text", Static)
        if dialog:
            dialog.update(
                Text(
                    "剧情已结束。感谢游玩！\n按 R 键返回标题画面。",
                    style=Style(color="bright_yellow"),
                )
            )
        char_art = self._query_safe("#char_art", Static)
        if char_art:
            school_art = get_scene_art("school")
            char_art.update(
                Text.assemble(
                    school_art,
                    Text("\n  锋焰高等学园", style=Style(color="grey70")),
                )
            )
        choices_container = self._query_safe("#choices_container", Vertical)
        if choices_container:
            choices_container.display = False
        self.showing_choices = False

    def _show_ending(self) -> None:
        """显示结局画面"""
        gs = self.app.game_state
        ch_label = self._query_safe("#chapter_label", Static)
        if ch_label:
            ch_label.update(Text("── 终章 ──", style=Style(color="bright_red", bold=True)))
        name_label = self._query_safe("#char_name_label", Static)
        if name_label:
            name_label.update(Text(""))
        end_text = "「炮鸣响彻赛场，炽焰永不息。」\n\n"
        end_text += f"已获得成就：{'、'.join(gs.achievements) if gs.achievements else '无'}\n\n"
        titles = gs.get_titles()
        end_text += f"隐藏称号：{'、'.join(titles) if titles else '未获得'}\n\n"
        end_text += "好感度总结：\n"
        for cid, name in [("sl", "苏凛"), ("xr", "夏燃"), ("wy", "温屿"), ("qy", "秋柚")]:
            hearts = "♥" * min(gs.affection[cid] // 2, 5)
            end_text += f"  {name}：{hearts} ({gs.affection[cid]})\n"
        end_text += "\n按 R 键返回标题画面。"
        dialog = self._query_safe("#dialog_text", Static)
        if dialog:
            dialog.update(Text(end_text, style=Style(color="bright_yellow")))
        char_art = self._query_safe("#char_art", Static)
        if char_art:
            school_art = get_scene_art("school")
            char_art.update(
                Text.assemble(
                    school_art,
                    Text("\n  锋焰高等学园", style=Style(color="grey70")),
                )
            )
        choices_container = self._query_safe("#choices_container", Vertical)
        if choices_container:
            choices_container.display = False
        self.showing_choices = False

    # ---- 动作 ----

    def action_advance(self) -> None:
        if self.showing_choices:
            return
        self._advance_scene()

    def action_choice_0(self) -> None:
        if self.showing_choices:
            self._handle_choice(0)

    def action_choice_1(self) -> None:
        if self.showing_choices:
            self._handle_choice(1)

    def action_choice_2(self) -> None:
        if self.showing_choices:
            self._handle_choice(2)

    def action_choice_3(self) -> None:
        if self.showing_choices:
            self._handle_choice(3)

    def action_save_game(self) -> None:
        self.app.push_screen(SaveLoadScreen(self.app.game_state, is_save=True))

    def action_load_game(self) -> None:
        self.app.push_screen(SaveLoadScreen(self.app.game_state, is_save=False))

    def action_show_affection(self) -> None:
        gs = self.app.game_state
        info = "── 好感度 ──\n"
        for cid, name in [("sl", "苏凛"), ("xr", "夏燃"), ("wy", "温屿"), ("qy", "秋柚")]:
            hearts = "♥" * min(gs.affection[cid] // 2, 10)
            info += f'{name}：{hearts} ({gs.affection[cid]})\n'
        info += f'\n成就：{"、".join(gs.achievements) if gs.achievements else "暂无"}'
        self.app.push_screen(MessageScreen(info, title="角色状态"))

    def action_show_menu(self) -> None:
        self.app.push_screen(SettingsScreen())

    def action_show_credits(self) -> None:
        self.app.push_screen(CreditsScreen())

    def action_return_title(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id and btn_id.startswith("choice_btn_"):
            idx = int(btn_id.split("_")[-1])
            if self.showing_choices:
                self._handle_choice(idx)


# ============================================================
# CSS 样式
# ============================================================

GAME_CSS = """
Screen {
    background: $surface;
}

#title_container {
    align: center middle;
    width: 100%;
    height: 100%;
}

#title_inner {
    align: center middle;
    width: 100%;
    max-width: 70;
    padding: 2 4;
    border: solid $accent;
}

#title_company {
    color: $secondary;
    text-align: center;
    width: 100%;
    padding-bottom: 1;
}

#title_logo {
    color: $warning;
    text-align: center;
    width: 100%;
    padding-bottom: 1;
}

#title_text {
    text-align: center;
    width: 100%;
    padding-bottom: 1;
}

#title_sub {
    text-align: center;
    width: 100%;
    padding-bottom: 1;
}

#title_disclaimer {
    text-align: center;
    width: 100%;
    padding-bottom: 2;
    color: $success;
}

#title_menu {
    text-align: center;
    width: 100%;
}

#game_container {
    width: 100%;
    height: 100%;
}

#game_area {
    width: 100%;
    height: 100%;
}

#char_panel {
    width: 38;
    min-width: 38;
    max-width: 38;
    height: 100%;
    border: solid $primary;
    background: $panel;
    padding: 1 1;
    align: center top;
}

#char_art {
    width: 100%;
    text-align: left;
}

#text_panel {
    width: 1fr;
    height: 100%;
    padding: 1 2;
    border: solid $primary-background;
    background: $boost;
}

#chapter_label {
    text-align: left;
    width: 100%;
    padding-bottom: 1;
    height: auto;
}

#char_name_label {
    text-align: left;
    width: 100%;
    padding-bottom: 1;
    height: auto;
}

#dialog_text {
    width: 100%;
    min-height: 5;
    border: dashed $primary-background;
    padding: 1 2;
    background: $surface;
}

#choices_container {
    margin-top: 1;
    width: 100%;
    display: none;
}

.choice-btn {
    width: 100%;
    margin-bottom: 1;
    text-align: left;
}

#msg_overlay {
    align: center middle;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.6);
}

#msg_inner {
    width: 50;
    padding: 2 3;
    border: solid $accent;
    background: $surface;
}

#msg_title {
    text-align: center;
    padding-bottom: 1;
    color: $accent;
}

#msg_body {
    padding-bottom: 2;
    text-align: center;
}

#msg_ok {
    width: 100%;
}

#sl_inner {
    width: 45;
    padding: 2 3;
    border: solid $accent;
    background: $surface;
}

#sl_title {
    text-align: center;
    padding-bottom: 1;
    color: $accent;
}

#sl_info {
    padding-bottom: 2;
    text-align: center;
}

#sl_buttons {
    width: 100%;
    align: center middle;
}

#sl_confirm, #sl_cancel {
    width: 20;
    margin: 0 1;
}

#settings_inner {
    width: 62;
    padding: 2 3;
    border: solid $accent;
    background: $surface;
}

#settings_title {
    text-align: center;
    padding-bottom: 1;
    color: $accent;
}

#settings_info {
    padding-bottom: 2;
}

#settings_buttons {
    width: 100%;
    align: center middle;
    padding-bottom: 1;
}

#music_toggle, #music_down, #music_up {
    width: 18;
    margin: 0 1;
}

#settings_close {
    width: 100%;
}

#credits_inner {
    width: 62;
    padding: 2 3;
    border: solid $accent;
    background: $surface;
}

#credits_title {
    text-align: center;
    padding-bottom: 1;
    color: $accent;
}

#credits_info {
    padding-bottom: 2;
}

#credits_close {
    width: 100%;
}
"""


# ============================================================
# 游戏主应用
# ============================================================


class ArtyGal(App):
    """炽焰炮阵：铸锋少年 - TUI互动视觉小说"""

    CSS = GAME_CSS
    BINDINGS = [
        Binding("q", "quit_game", "退出"),
    ]
    game_state: GameState
    audio: AudioManager

    def on_mount(self) -> None:
        self.game_state = GameState()
        self.audio = AudioManager(MUSIC_FILE)
        self.audio.start()
        self.push_screen(TitleScreen())

    def action_quit_game(self) -> None:
        if hasattr(self, "audio"):
            self.audio.close()
        self.exit()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    ArtyGal().run()
