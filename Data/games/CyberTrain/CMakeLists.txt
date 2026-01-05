cmake_minimum_required(VERSION 3.11)
project(CyberTrain)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find or include Raylib
# Option 1: If Raylib is installed system-wide
find_package(raylib QUIET)

# Option 2: If using a local Raylib installation
# You may need to adjust these paths based on your Raylib installation
if(NOT raylib_FOUND)
    # Try to find Raylib in common locations
    set(RAYLIB_INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/raylib/include" 
                            "${CMAKE_CURRENT_SOURCE_DIR}/../raylib/src"
                            "/usr/local/include"
                            "/usr/include")
    
    set(RAYLIB_LIBRARIES "${CMAKE_CURRENT_SOURCE_DIR}/raylib/lib/libraylib.a"
                         "${CMAKE_CURRENT_SOURCE_DIR}/../raylib/src/libraylib.a"
                         "/usr/local/lib/libraylib.a"
                         "/usr/lib/libraylib.a")
    
    find_path(RAYLIB_INCLUDE_DIR raylib.h PATHS ${RAYLIB_INCLUDE_DIRS})
    find_library(RAYLIB_LIBRARY NAMES raylib PATHS ${RAYLIB_LIBRARIES})
    
    if(RAYLIB_INCLUDE_DIR AND RAYLIB_LIBRARY)
        set(raylib_FOUND TRUE)
        message(STATUS "Found Raylib: ${RAYLIB_LIBRARY}")
    endif()
endif()

# If still not found, provide instructions
if(NOT raylib_FOUND)
    message(WARNING "Raylib not found. Please install Raylib or adjust CMakeLists.txt paths.")
    message(STATUS "You can download Raylib from: https://www.raylib.com/")
    message(STATUS "Or use: git clone https://github.com/raysan5/raylib.git")
endif()

# Source files
add_executable(${PROJECT_NAME} main.cpp)

# Link libraries
if(raylib_FOUND)
    target_include_directories(${PROJECT_NAME} PRIVATE ${RAYLIB_INCLUDE_DIR})
    target_link_libraries(${PROJECT_NAME} ${RAYLIB_LIBRARY})
    
    # Platform-specific libraries
    if(WIN32)
        target_link_libraries(${PROJECT_NAME} winmm)
    elseif(APPLE)
        find_library(COCOA_LIBRARY Cocoa)
        find_library(IOKIT_LIBRARY IOKit)
        find_library(OPENGL_LIBRARY OpenGL)
        target_link_libraries(${PROJECT_NAME} ${COCOA_LIBRARY} ${IOKIT_LIBRARY} ${OPENGL_LIBRARY})
    elseif(UNIX)
        target_link_libraries(${PROJECT_NAME} pthread dl m)
    endif()
endif()

