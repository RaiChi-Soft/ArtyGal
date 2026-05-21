from pathlib import Path
from rich.ansi import AnsiDecoder
from rich.text import Text
from textual.app import App
from textual.widgets import Static

def load_ansi_art(file_path: str) -> Text:
    # .ans 文件使用 CP437 编码
    ansi_content = Path(file_path).read_text(encoding='cp437')
    decoder = AnsiDecoder()
    # decode 返回生成器，取第一个 Text 片段（整个 ANSI 文件通常只有一个主片段）
    return next(decoder.decode(ansi_content))

class MyApp(App):
    def compose(self):
        ansi_text = load_ansi_art('ansi_art/sl.ans')
        yield Static(ansi_text)

if __name__ == "__main__":
    MyApp().run()