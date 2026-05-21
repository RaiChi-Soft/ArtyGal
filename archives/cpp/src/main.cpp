#include <zlib.h>

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#endif

#include "ftxui/component/component.hpp"
#include "ftxui/component/screen_interactive.hpp"
#include "ftxui/dom/elements.hpp"
#include "resources.hpp"

using namespace ftxui;

namespace {

struct Choice {
  std::string text;
  std::string next;
  std::map<std::string, int> affection;
  std::string achievement;
};

struct Scene {
  std::string id;
  int chapter = 0;
  std::string title;
  std::string bg;
  std::vector<std::string> characters;
  std::string speaker_id;
  std::string speaker_name;
  bool narrator = false;
  bool chapter_end = false;
  bool final_ending = false;
  std::string text;
  std::vector<Choice> choices;
};

struct Story {
  std::string title = "炽焰炮阵：铸锋少年";
  std::string subtitle = "以炮为魂，以火为志，热血逐梦军械之路";
  std::vector<Scene> scenes;
  std::unordered_map<std::string, std::size_t> id_to_index;
};

struct Rgb {
  int r = 255;
  int g = 255;
  int b = 255;
};

struct Cell {
  std::string glyph = " ";
  std::optional<Rgb> fg;
  std::optional<Rgb> bg;
};

struct GameState {
  std::size_t scene_index = 0;
  std::map<std::string, int> affection{{"sl", 0}, {"xr", 0}, {"wy", 0}, {"qy", 0}};
  std::vector<std::string> achievements;
  bool title_screen = true;
  std::string overlay;
};

std::string DecompressGzip(const artygal::embedded::Resource& resource) {
  std::string out(resource.original_size, '\0');
  z_stream stream{};
  stream.next_in = const_cast<Bytef*>(resource.gzip_data);
  stream.avail_in = static_cast<uInt>(resource.gzip_size);
  stream.next_out = reinterpret_cast<Bytef*>(out.data());
  stream.avail_out = static_cast<uInt>(out.size());

  if (inflateInit2(&stream, 16 + MAX_WBITS) != Z_OK) {
    throw std::runtime_error("inflateInit2 failed");
  }
  const int rc = inflate(&stream, Z_FINISH);
  inflateEnd(&stream);
  if (rc != Z_STREAM_END) {
    throw std::runtime_error("gzip inflate failed");
  }
  return out;
}

std::string ResourceText(const std::string& name) {
  for (const auto& resource : artygal::embedded::kResources) {
    if (name == resource.name) {
      return DecompressGzip(resource);
    }
  }
  return {};
}

std::vector<std::string> Split(const std::string& text, char delim) {
  std::vector<std::string> fields;
  std::string current;
  std::stringstream stream(text);
  while (std::getline(stream, current, delim)) {
    fields.push_back(current);
  }
  if (!text.empty() && text.back() == delim) {
    fields.emplace_back();
  }
  return fields;
}

std::string Unescape(std::string text) {
  std::string out;
  for (std::size_t i = 0; i < text.size(); ++i) {
    if (text[i] == '\\' && i + 1 < text.size()) {
      const char next = text[++i];
      if (next == 'p') out.push_back('|');
      else if (next == 'n') out.push_back('\n');
      else out.push_back(next);
    } else {
      out.push_back(text[i]);
    }
  }
  return out;
}

std::vector<std::string> SplitCsv(const std::string& text) {
  std::vector<std::string> out;
  for (auto item : Split(text, ',')) {
    if (!item.empty()) out.push_back(item);
  }
  return out;
}

std::map<std::string, int> ParseAffection(const std::string& text) {
  std::map<std::string, int> result;
  for (const auto& item : Split(text, ',')) {
    auto pair = Split(item, ':');
    if (pair.size() == 2 && !pair[0].empty()) {
      result[pair[0]] = std::stoi(pair[1]);
    }
  }
  return result;
}

Story ParseStory(const std::string& script) {
  Story story;
  auto lines = Split(script, '\n');
  for (std::size_t i = 0; i < lines.size();) {
    if (!lines[i].empty() && lines[i].back() == '\r') lines[i].pop_back();
    if (lines[i].empty() || lines[i][0] == '#') {
      ++i;
      continue;
    }

    auto header = Split(lines[i], '|');
    if (header[0] == "META" && header.size() >= 3) {
      if (header[1] == "title") story.title = Unescape(header[2]);
      if (header[1] == "subtitle") story.subtitle = Unescape(header[2]);
      ++i;
      continue;
    }

    if (header[0] != "SCENE" || header.size() < 11) {
      ++i;
      continue;
    }

    Scene scene;
    scene.id = Unescape(header[1]);
    scene.chapter = std::stoi(header[2]);
    scene.title = Unescape(header[3]);
    scene.bg = Unescape(header[4]);
    scene.characters = SplitCsv(Unescape(header[5]));
    scene.speaker_id = Unescape(header[6]);
    scene.speaker_name = Unescape(header[7]);
    scene.narrator = header[8] == "1";
    scene.chapter_end = header[9] == "1";
    scene.final_ending = header[10] == "1";
    ++i;

    if (i < lines.size() && lines[i] == "TEXT") {
      ++i;
      std::string text;
      while (i < lines.size() && lines[i] != "ENDTEXT") {
        if (!lines[i].empty() && lines[i].back() == '\r') lines[i].pop_back();
        if (!text.empty()) text += '\n';
        text += lines[i++];
      }
      scene.text = text;
      if (i < lines.size()) ++i;
    }

    while (i < lines.size() && lines[i] != "ENDSCENE") {
      if (!lines[i].empty() && lines[i].back() == '\r') lines[i].pop_back();
      auto parts = Split(lines[i], '|');
      if (parts.size() >= 5 && parts[0] == "CHOICE") {
        Choice choice;
        choice.text = Unescape(parts[1]);
        choice.next = Unescape(parts[2]);
        choice.affection = ParseAffection(Unescape(parts[3]));
        choice.achievement = Unescape(parts[4]);
        scene.choices.push_back(std::move(choice));
      }
      ++i;
    }
    if (i < lines.size()) ++i;
    story.id_to_index[scene.id] = story.scenes.size();
    story.scenes.push_back(std::move(scene));
  }
  return story;
}

std::size_t Utf8CharLen(unsigned char c) {
  if ((c & 0x80) == 0) return 1;
  if ((c & 0xE0) == 0xC0) return 2;
  if ((c & 0xF0) == 0xE0) return 3;
  if ((c & 0xF8) == 0xF0) return 4;
  return 1;
}

std::vector<int> ParseSgrNumbers(const std::string& text) {
  std::vector<int> nums;
  std::string token;
  for (char c : text) {
    if (c == ';') {
      nums.push_back(token.empty() ? 0 : std::stoi(token));
      token.clear();
    } else if (std::isdigit(static_cast<unsigned char>(c))) {
      token.push_back(c);
    }
  }
  nums.push_back(token.empty() ? 0 : std::stoi(token));
  return nums;
}

std::vector<std::vector<Cell>> ParseAnsiArt(const std::string& ansi) {
  std::vector<std::vector<Cell>> rows(1);
  std::optional<Rgb> fg;
  std::optional<Rgb> bg;

  for (std::size_t i = 0; i < ansi.size();) {
    if (ansi[i] == '\r') {
      ++i;
      continue;
    }
    if (ansi[i] == '\n') {
      rows.emplace_back();
      ++i;
      continue;
    }
    if (ansi[i] == '\x1b' && i + 1 < ansi.size() && ansi[i + 1] == '[') {
      const auto end = ansi.find('m', i + 2);
      if (end == std::string::npos) break;
      auto nums = ParseSgrNumbers(ansi.substr(i + 2, end - (i + 2)));
      for (std::size_t n = 0; n < nums.size(); ++n) {
        if (nums[n] == 0) {
          fg.reset();
          bg.reset();
        } else if (nums[n] == 38 && n + 4 < nums.size() && nums[n + 1] == 2) {
          fg = Rgb{nums[n + 2], nums[n + 3], nums[n + 4]};
          n += 4;
        } else if (nums[n] == 48 && n + 4 < nums.size() && nums[n + 1] == 2) {
          bg = Rgb{nums[n + 2], nums[n + 3], nums[n + 4]};
          n += 4;
        }
      }
      i = end + 1;
      continue;
    }

    const std::size_t len = Utf8CharLen(static_cast<unsigned char>(ansi[i]));
    Cell cell;
    cell.glyph = ansi.substr(i, std::min(len, ansi.size() - i));
    cell.fg = fg;
    cell.bg = bg;
    rows.back().push_back(std::move(cell));
    i += len;
  }

  while (!rows.empty() && rows.back().empty()) rows.pop_back();
  return rows;
}

Element CellElement(const Cell& cell) {
  auto e = text(cell.glyph);
  if (cell.fg) e = e | color(Color::RGB(cell.fg->r, cell.fg->g, cell.fg->b));
  if (cell.bg) e = e | bgcolor(Color::RGB(cell.bg->r, cell.bg->g, cell.bg->b));
  return e;
}

Element AnsiElement(const std::string& resource_name) {
  static std::unordered_map<std::string, std::vector<std::vector<Cell>>> cache;
  if (!cache.count(resource_name)) {
    cache[resource_name] = ParseAnsiArt(ResourceText(resource_name));
  }
  Elements lines;
  for (const auto& row : cache[resource_name]) {
    Elements cells;
    cells.reserve(row.size());
    for (const auto& cell : row) cells.push_back(CellElement(cell));
    lines.push_back(hbox(std::move(cells)));
  }
  return vbox(std::move(lines));
}

std::string CharacterName(const std::string& id) {
  static const std::map<std::string, std::string> names{
      {"sl", "苏凛"}, {"xr", "夏燃"}, {"wy", "温屿"}, {"qy", "秋柚"}, {"xg", "小G"}};
  auto it = names.find(id);
  return it == names.end() ? id : it->second;
}

std::string SceneName(const std::string& id) {
  static const std::map<std::string, std::string> names{
      {"school", "锋焰高等学园"}, {"workshop", "火炮同好社"}, {"range", "训练靶场"}};
  auto it = names.find(id);
  return it == names.end() ? id : it->second;
}

void AddAchievement(GameState& state, const std::string& achievement) {
  if (achievement.empty()) return;
  if (std::find(state.achievements.begin(), state.achievements.end(), achievement) ==
      state.achievements.end()) {
    state.achievements.push_back(achievement);
  }
}

std::string Join(const std::vector<std::string>& items, const std::string& sep) {
  std::string out;
  for (std::size_t i = 0; i < items.size(); ++i) {
    if (i) out += sep;
    out += items[i];
  }
  return out;
}

std::size_t FirstSceneOfNextChapter(const Story& story, std::size_t current) {
  const int chapter = story.scenes[current].chapter;
  for (std::size_t i = current + 1; i < story.scenes.size(); ++i) {
    if (story.scenes[i].chapter > chapter) return i;
  }
  return story.scenes.size();
}

void Advance(const Story& story, GameState& state) {
  if (state.title_screen || state.scene_index >= story.scenes.size()) return;
  const Scene& scene = story.scenes[state.scene_index];
  if (scene.final_ending) {
    state.overlay = "ending";
    return;
  }
  if (!scene.choices.empty()) return;
  if (scene.chapter_end) {
    state.scene_index = FirstSceneOfNextChapter(story, state.scene_index);
  } else {
    ++state.scene_index;
  }
  if (state.scene_index >= story.scenes.size()) state.overlay = "ending";
}

void Choose(const Story& story, GameState& state, int index) {
  if (state.scene_index >= story.scenes.size()) return;
  const Scene& scene = story.scenes[state.scene_index];
  if (index < 0 || index >= static_cast<int>(scene.choices.size())) return;
  const Choice& choice = scene.choices[index];
  for (const auto& [id, delta] : choice.affection) state.affection[id] += delta;
  AddAchievement(state, choice.achievement);
  auto found = story.id_to_index.find(choice.next);
  if (found != story.id_to_index.end()) state.scene_index = found->second;
}

std::string SavePath() {
  return "artygal_save.txt";
}

void SaveGame(const Story& story, const GameState& state) {
  std::ofstream file(SavePath(), std::ios::binary);
  file << (state.scene_index < story.scenes.size() ? story.scenes[state.scene_index].id : "") << "\n";
  for (const auto& [id, value] : state.affection) file << id << "=" << value << "\n";
  file << "achievements=" << Join(state.achievements, ",") << "\n";
}

bool LoadGame(const Story& story, GameState& state) {
  std::ifstream file(SavePath(), std::ios::binary);
  if (!file) return false;
  std::string line;
  std::getline(file, line);
  auto found = story.id_to_index.find(line);
  if (found == story.id_to_index.end()) return false;
  state.scene_index = found->second;
  state.title_screen = false;
  while (std::getline(file, line)) {
    auto pair = Split(line, '=');
    if (pair.size() < 2) continue;
    if (pair[0] == "achievements") {
      state.achievements = SplitCsv(pair[1]);
    } else if (state.affection.count(pair[0])) {
      state.affection[pair[0]] = std::stoi(pair[1]);
    }
  }
  return true;
}

Element LeftArt(const Scene& scene) {
  Elements blocks;
  if (scene.characters.empty()) {
    blocks.push_back(AnsiElement("ansi_art/" + scene.bg + ".ans"));
    blocks.push_back(text("  " + SceneName(scene.bg)) | color(Color::GrayLight));
  } else {
    for (const auto& id : scene.characters) {
      blocks.push_back(AnsiElement("ansi_art/" + id + ".ans"));
      blocks.push_back(text("  " + CharacterName(id)) | color(Color::GrayLight));
      blocks.push_back(text(""));
    }
  }
  return vbox(std::move(blocks)) | size(WIDTH, EQUAL, 38);
}

Element StatusText(const GameState& state) {
  Elements rows;
  rows.push_back(text("好感度") | bold | color(Color::Cyan));
  for (const auto& [id, value] : state.affection) {
    rows.push_back(text(CharacterName(id) + "：" + std::string(std::max(0, value / 2), '*') +
                        " (" + std::to_string(value) + ")"));
  }
  rows.push_back(separator());
  rows.push_back(text("成就：" + (state.achievements.empty() ? std::string("暂无")
                                                      : Join(state.achievements, "、"))));
  return vbox(std::move(rows));
}

Element Modal(const std::string& title, Element body) {
  return window(text(" " + title + " "), body | size(WIDTH, GREATER_THAN, 48)) | clear_under;
}

Element Render(const Story& story, const GameState& state) {
  if (state.title_screen) {
    return vbox({
               filler(),
               text(story.title) | bold | color(Color::Yellow) | center,
               text(story.subtitle) | color(Color::GrayLight) | center,
               separatorEmpty(),
               AnsiElement("ansi_art/school.ans") | center,
               separatorEmpty(),
               text("[Enter] 开始新游戏    [L] 读取存档    [Q] 退出") | center,
               filler(),
           }) |
           border;
  }

  if (state.scene_index >= story.scenes.size()) {
    return Modal("终剧", vbox({text("剧情已结束。感谢游玩。"), separator(), StatusText(state),
                              text("按 R 返回标题，或 Q 退出。")}));
  }

  const Scene& scene = story.scenes[state.scene_index];
  Elements choice_rows;
  for (std::size_t i = 0; i < scene.choices.size(); ++i) {
    choice_rows.push_back(text("[" + std::to_string(i + 1) + "] " + scene.choices[i].text) |
                          color(Color::Yellow));
  }
  if (choice_rows.empty()) choice_rows.push_back(text("按 Enter 继续") | color(Color::GrayLight));

  auto speaker = scene.narrator ? std::string("── 旁白 ──") : ("▎ " + scene.speaker_name);
  auto main_view =
      hbox({
          LeftArt(scene) | border,
          vbox({
              text(scene.title) | bold | color(Color::Cyan),
              text(speaker) | color(scene.narrator ? Color::GrayLight : Color::Green),
              separator(),
              paragraph(scene.text) | color(Color::White),
              separator(),
              vbox(std::move(choice_rows)),
              filler(),
              text("[S]存档 [L]读档 [A]状态 [M]菜单 [R]标题 [Q]退出") | color(Color::GrayLight),
          }) | flex | border,
      });

  if (state.overlay == "status") {
    return dbox(main_view, Modal("角色状态", vbox({StatusText(state), separator(), text("按 Enter 关闭")})) | center);
  }
  if (state.overlay == "help") {
    return dbox(main_view,
                Modal("操作说明",
                      vbox({text("Enter：继续剧情"), text("1-4：选择分支"), text("S/L：保存/读取"),
                            text("A：查看状态"), text("R：返回标题"), text("Q：退出"),
                            separator(), text("按 Enter 关闭")})) |
                    center);
  }
  if (state.overlay == "ending") {
    return dbox(main_view,
                Modal("结局总结", vbox({text("炮鸣响彻赛场，炽焰永不息。"), separator(),
                                       StatusText(state), separator(), text("按 R 返回标题，或 Q 退出。")})) |
                    center);
  }
  if (!state.overlay.empty()) {
    return dbox(main_view, Modal("系统", vbox({text(state.overlay), separator(), text("按 Enter 关闭")})) | center);
  }
  return main_view;
}

}  // namespace

int main() {
#ifdef _WIN32
  SetConsoleOutputCP(CP_UTF8);
  SetConsoleCP(CP_UTF8);
#endif

  Story story = ParseStory(ResourceText("story.gal"));
  GameState state;
  auto screen = ScreenInteractive::Fullscreen();

  auto renderer = Renderer([&] { return Render(story, state); });
  auto component = CatchEvent(renderer, [&](Event event) {
    if (!state.overlay.empty()) {
      if (event == Event::Return || event == Event::Escape) {
        state.overlay.clear();
        return true;
      }
      if (event == Event::Character("r") || event == Event::Character("R")) {
        state = GameState{};
        return true;
      }
    }

    if (event == Event::Character("q") || event == Event::Character("Q")) {
      screen.ExitLoopClosure()();
      return true;
    }
    if (state.title_screen) {
      if (event == Event::Return) {
        state = GameState{};
        state.title_screen = false;
        return true;
      }
      if (event == Event::Character("l") || event == Event::Character("L")) {
        if (!LoadGame(story, state)) state.overlay = "没有找到可用存档。";
        return true;
      }
      return false;
    }

    if (event == Event::Return) {
      Advance(story, state);
      return true;
    }
    for (int i = 0; i < 4; ++i) {
      if (event == Event::Character(std::to_string(i + 1))) {
        Choose(story, state, i);
        return true;
      }
    }
    if (event == Event::Character("s") || event == Event::Character("S")) {
      SaveGame(story, state);
      state.overlay = "存档成功。";
      return true;
    }
    if (event == Event::Character("l") || event == Event::Character("L")) {
      if (!LoadGame(story, state)) state.overlay = "读取存档失败。";
      return true;
    }
    if (event == Event::Character("a") || event == Event::Character("A")) {
      state.overlay = "status";
      return true;
    }
    if (event == Event::Character("m") || event == Event::Character("M")) {
      state.overlay = "help";
      return true;
    }
    if (event == Event::Character("r") || event == Event::Character("R")) {
      state = GameState{};
      return true;
    }
    return false;
  });

  screen.Loop(component);
  return 0;
}
