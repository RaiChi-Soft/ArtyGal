cmake_minimum_required(VERSION 3.24)

project(ArtyGalCpp VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)

set(ARTYGAL_FTXUI_DIR "" CACHE PATH "Path to a local FTXUI checkout")
if(ARTYGAL_FTXUI_DIR)
  add_subdirectory(${ARTYGAL_FTXUI_DIR} ${CMAKE_BINARY_DIR}/ftxui-local)
elseif(EXISTS ${CMAKE_CURRENT_LIST_DIR}/vendor/FTXUI/CMakeLists.txt)
  add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/vendor/FTXUI ${CMAKE_BINARY_DIR}/ftxui-local)
else()
  FetchContent_Declare(
    ftxui
    GIT_REPOSITORY https://github.com/ArthurSonzogni/FTXUI.git
    GIT_TAG main
  )
  FetchContent_MakeAvailable(ftxui)
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(ZLIB REQUIRED)

set(ROOT_DIR ${CMAKE_CURRENT_LIST_DIR}/..)
set(GENERATED_DIR ${CMAKE_CURRENT_BINARY_DIR}/generated)
set(GENERATED_RESOURCES ${GENERATED_DIR}/resources.hpp)

file(GLOB ANSI_RESOURCES CONFIGURE_DEPENDS ${ROOT_DIR}/ansi_art/*.ans)

add_custom_command(
  OUTPUT ${GENERATED_RESOURCES}
  COMMAND ${CMAKE_COMMAND} -E make_directory ${GENERATED_DIR}
  COMMAND ${Python3_EXECUTABLE}
          ${ROOT_DIR}/tools/embed_resources.py
          --root ${ROOT_DIR}
          --out ${GENERATED_RESOURCES}
  DEPENDS
          ${ROOT_DIR}/tools/embed_resources.py
          ${ROOT_DIR}/assets/story.gal
          ${ANSI_RESOURCES}
  COMMENT "Embedding gzip-compressed story and ANSI resources"
  VERBATIM
)

add_executable(artygal
  src/main.cpp
  ${GENERATED_RESOURCES}
)

target_include_directories(artygal PRIVATE ${GENERATED_DIR})
target_link_libraries(artygal
  PRIVATE
    ftxui::screen
    ftxui::dom
    ftxui::component
    ZLIB::ZLIB
)

if(MINGW)
  target_link_options(artygal PRIVATE -static-libgcc -static-libstdc++)
endif()
