#!/usr/bin/env python3
"""
《炽焰炮阵：铸锋少年》GALGAME - TUI互动视觉小说
使用 Textual 框架构建，支持 ANSI 角色立绘、多线剧情、好感度与成就系统
"""

from __future__ import annotations

import json
import os
import re
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

# ANSI资源目录
ANSI_DIR: Path = Path("ansi_art")

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
        Binding("q", "quit", "退出游戏"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Label("", id="title_logo"),
                Static("", id="title_text"),
                Static("", id="title_sub"),
                Static("", id="title_menu"),
                id="title_inner",
            ),
            id="title_container",
        )
        yield Footer()

    def on_mount(self) -> None:
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
        title_sub.update(
            Text(
                "少年以毕生热忱献身火炮军械\n"
                "以炮为魂·以火为志·热血逐梦军械之路",
                style=Style(color="grey70", italic=True),
            )
        )
        title_menu = self.query_one("#title_menu", Static)
        title_menu.update(
            Text(
                "[ Enter ] 开始新游戏\n"
                "[  L   ] 读取存档\n"
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

        # 检查是否是章节结束
        if scene.get("chapter_end"):
            self.current_group_index += 1
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
        next_id = choice["next"]
        group = self._get_current_group()
        scenes = group.get("scenes", [])
        found = False
        for i, s in enumerate(scenes):
            if s.get("id") == next_id:
                self.current_scene_index = i
                found = True
                break

        if not found:
            # 搜索所有场景组
            for gi, grp in enumerate(STORY_SCRIPT):
                for si, s in enumerate(grp.get("scenes", [])):
                    if s.get("id") == next_id:
                        self.current_group_index = gi
                        self.current_scene_index = si
                        found = True
                        break
                if found:
                    break

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
            char_art.update(Text(""))
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
            char_art.update(Text(""))
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
        self.app.push_screen(
            MessageScreen(
                "[Enter] 继续剧情\n"
                "[1-4] 选择分支\n"
                "[S] 保存进度\n"
                "[L] 读取存档\n"
                "[A] 查看好感度\n"
                "[R] 返回标题\n"
                "[Q] 退出游戏",
                title="操作说明",
            )
        )

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
    padding-bottom: 2;
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

    def on_mount(self) -> None:
        self.game_state = GameState()
        self.push_screen(TitleScreen())

    def action_quit_game(self) -> None:
        self.exit()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    ArtyGal().run()
