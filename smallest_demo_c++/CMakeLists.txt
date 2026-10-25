cmake_minimum_required(VERSION 3.5)
set(project "weixue_st3215_control")
project(${project})

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -O3")

# 告诉编译器去当前目录下的 sdk 文件夹里找头文件和库
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/sdk)
link_directories(${CMAKE_CURRENT_SOURCE_DIR}/sdk)
link_libraries(libSCServo.a)

# 只抓取当前目录下的 cpp 和 h 文件，不要去抓 sdk 里面的
file(GLOB hdrs *.h)
file(GLOB srs *.cpp)

add_executable(${project} ${hdrs} ${srs})