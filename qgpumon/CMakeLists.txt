cmake_minimum_required(VERSION 3.21)
project(qgpumon VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)
qt_standard_project_setup()

# GUI app (no console window) + a small console CLI for diagnostics
qt_add_executable(qgpumon WIN32
    src/main.cpp
)
target_link_libraries(qgpumon PRIVATE Qt6::Widgets)

qt_add_resources(qgpumon "resources" FILES icon.ico)
