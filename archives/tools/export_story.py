#!/usr/bin/env python3
"""Export the Python prototype story into the editable C++ story script format."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PY_GAME = ROOT / "galgame.py"
OUT = ROOT / "assets" / "story.gal"


CHAPTER_OPENERS = {
    1: "晨雾还挂在锋焰高等学园的炮塔纪念碑上。远处训练场传来低沉的试射声，像某种只属于军械少年的召唤。",
    2: "入社后的第一周，小G终于明白：火炮不是孤独的钢铁，而是一整支队伍互相信任后的合奏。",
    3: "地区联赛的报名表被钉在公告栏上。纸页很薄，却像一张通往更大赛场的作战地图。",
    4: "黑岩工高的到来让空气变得紧绷。两种火炮理念第一次正面相撞，连工作室里的螺栓都像在等待答案。",
    5: "全国赛前的夜晚，社团灯火未熄。每个人都在把自己的执念，拧进那门即将诞生的新炮里。",
    6: "全国赛场比想象中更巨大。观众席的声浪翻涌而来，小G却只听见炮闩闭合时清脆的一声。",
    7: "所有炮声都会消散，但被炮声点燃的人不会。最后的选择，开始变得比胜负更沉重。",
}

BG_DETAILS = {
    "school": [
        "校园大道两侧挂着历届军械赛的旗帜。风一吹，旗面猎猎作响，像旧时代炮兵阵地上展开的识别旗。",
        "教学楼的玻璃映出年轻人的身影，也映出远处陈列炮冰冷的轮廓。",
    ],
    "workshop": [
        "工作台上摊着弹道表、旧炮闩和磨损的扳手。灯光落在金属边缘，亮得像未熄的火星。",
        "空气里混着机油、铁屑和擦炮布的味道。这里破旧，却比任何豪华社团室都更接近梦想。",
    ],
    "range": [
        "靶场尽头的风向袋微微摆动。每一阵风，都可能把胜负推偏几个看不见的角分。",
        "白线、靶标、观测镜和安全旗依次排开，整片场地像一张等待计算的巨大弹道图。",
    ],
}

TECH_DETAILS = [
    ("测量", "小G把读数记在掌心旁的便签上。数字很小，却决定着炮膛寿命、精度，甚至一支队伍的尊严。"),
    ("炮架", "炮架不是支撑物那么简单。它要吞下后坐力，还要在下一发装填前把炮身稳稳送回原位。"),
    ("弹道", "温屿在草稿纸上画出一条弧线。那条线越过风、湿度和重力，最后落在所有人的心跳上。"),
    ("维护", "秋柚把每颗螺帽按顺序摆好。她说装备也会记得谁认真对待过它。"),
    ("试射", "炮声之后，所有人都没有立刻说话。他们先看烟、看弹着、看那一瞬间暴露出来的真实。"),
    ("全国赛", "全国赛不是更大的地区赛。那里每一个对手都带着自己的时代、流派和不可退让的骄傲。"),
]


def literal_story() -> list[dict]:
    module = ast.parse(PY_GAME.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "STORY_SCRIPT":
            return ast.literal_eval(node.value)
    raise RuntimeError("STORY_SCRIPT not found")


def esc(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("\\", "\\\\").replace("|", "\\p").replace("\n", "\\n")


def affection_text(choice: dict) -> str:
    affection = choice.get("affection", {})
    return ",".join(f"{k}:{v}" for k, v in affection.items())


def emit_scene(
    lines: list[str],
    *,
    scene_id: str,
    chapter: int,
    title: str,
    bg: str,
    chars: list[str],
    speaker: str,
    speaker_name: str,
    narrator: bool,
    text: str,
    chapter_end: bool = False,
    final_ending: bool = False,
    choices: list[dict] | None = None,
) -> None:
    lines.append(
        "|".join(
            [
                "SCENE",
                esc(scene_id),
                str(chapter),
                esc(title),
                esc(bg),
                esc(",".join(chars)),
                esc(speaker),
                esc(speaker_name),
                "1" if narrator else "0",
                "1" if chapter_end else "0",
                "1" if final_ending else "0",
            ]
        )
    )
    lines.append("TEXT")
    lines.extend(text.splitlines() or [""])
    lines.append("ENDTEXT")
    for choice in choices or []:
        lines.append(
            "|".join(
                [
                    "CHOICE",
                    esc(choice.get("text", "")),
                    esc(choice.get("next", "")),
                    esc(affection_text(choice)),
                    esc(choice.get("achievement", "")),
                ]
            )
        )
    lines.append("ENDSCENE")
    lines.append("")


def enrichment_after(scene: dict) -> str | None:
    text = scene.get("text", "")
    for keyword, detail in TECH_DETAILS:
        if keyword in text:
            return detail
    return None


def main() -> None:
    story = literal_story()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# 《炽焰炮阵：铸锋少年》外部剧本",
        "# 格式由 tools/export_story.py 生成；C++ 运行时代码只解析本文件，不内置剧情正文。",
        "META|title|炽焰炮阵：铸锋少年",
        "META|subtitle|以炮为魂，以火为志，热血逐梦军械之路",
        "",
    ]

    opened_chapters: set[int] = set()
    inserted_bg_count: dict[str, int] = {}
    seen_scene_ids: dict[str, int] = {}

    def unique_id(scene_id: str) -> str:
        count = seen_scene_ids.get(scene_id, 0)
        seen_scene_ids[scene_id] = count + 1
        return scene_id if count == 0 else f"{scene_id}_{count + 1}"

    for group_index, group in enumerate(story):
        chapter = int(group["chapter"])
        title = group["title"]
        if chapter not in opened_chapters and chapter in CHAPTER_OPENERS:
            opened_chapters.add(chapter)
            emit_scene(
                lines,
                scene_id=f"ch{chapter}_prologue",
                chapter=chapter,
                title=title,
                bg=group["scenes"][0].get("bg", "school"),
                chars=[],
                speaker="",
                speaker_name="",
                narrator=True,
                text=CHAPTER_OPENERS[chapter],
            )

        for scene in group.get("scenes", []):
            emit_scene(
                lines,
                scene_id=unique_id(scene["id"]),
                chapter=chapter,
                title=title,
                bg=scene.get("bg", ""),
                chars=scene.get("characters", []),
                speaker=scene.get("character", ""),
                speaker_name=scene.get("char_name", ""),
                narrator=bool(scene.get("narrator")),
                text=scene.get("text", ""),
                chapter_end=bool(scene.get("chapter_end")),
                final_ending=bool(scene.get("final_ending")),
                choices=scene.get("choices", []),
            )

            if scene.get("choices") or scene.get("chapter_end") or scene.get("final_ending"):
                continue

            detail = enrichment_after(scene)
            if detail:
                emit_scene(
                    lines,
                    scene_id=f"{scene['id']}_detail",
                    chapter=chapter,
                    title=title,
                    bg=scene.get("bg", ""),
                    chars=[],
                    speaker="",
                    speaker_name="",
                    narrator=True,
                    text=detail,
                )
                continue

            bg = scene.get("bg", "")
            count = inserted_bg_count.get(bg, 0)
            details = BG_DETAILS.get(bg, [])
            if not scene.get("characters") and details and count < len(details):
                inserted_bg_count[bg] = count + 1
                emit_scene(
                    lines,
                    scene_id=f"{scene['id']}_atmo",
                    chapter=chapter,
                    title=title,
                    bg=bg,
                    chars=[],
                    speaker="",
                    speaker_name="",
                    narrator=True,
                    text=details[count],
                )

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
