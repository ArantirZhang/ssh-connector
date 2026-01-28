cmake_minimum_required(VERSION 3.16)
project(ssh-connector VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# UI toolkit selection
set(UI_TOOLKIT "FLTK" CACHE STRING "UI toolkit to use (Qt or FLTK)")
set_property(CACHE UI_TOOLKIT PROPERTY STRINGS "Qt" "FLTK")
message(STATUS "Building with UI toolkit: ${UI_TOOLKIT}")

# Static linking option
option(BUILD_STATIC "Build with static libraries" OFF)
if(BUILD_STATIC)
    message(STATUS "Static linking enabled")
    if(WIN32)
        set(CMAKE_FIND_LIBRARY_SUFFIXES .lib .a)
    else()
        set(CMAKE_FIND_LIBRARY_SUFFIXES .a)
    endif()
    if(NOT DEFINED VCPKG_TARGET_TRIPLET)
        if(APPLE)
            if(CMAKE_SYSTEM_PROCESSOR STREQUAL "arm64")
                set(VCPKG_TARGET_TRIPLET "arm64-osx" CACHE STRING "")
            else()
                set(VCPKG_TARGET_TRIPLET "x64-osx" CACHE STRING "")
            endif()
        elseif(WIN32)
            set(VCPKG_TARGET_TRIPLET "x64-windows-static" CACHE STRING "")
        else()
            set(VCPKG_TARGET_TRIPLET "x64-linux" CACHE STRING "")
        endif()
    endif()
endif()

# Common source files (core logic)
set(COMMON_SOURCES
    src/config/Config.cpp
    src/config/ConfigManager.cpp
    src/core/SSHClient.cpp
    src/core/TunnelHandler.cpp
)

set(COMMON_HEADERS
    src/config/Config.h
    src/config/ConfigManager.h
    src/core/ConnectionState.h
    src/core/SSHClient.h
    src/core/TunnelHandler.h
)

# Find libssh
find_package(libssh QUIET CONFIG)
if(libssh_FOUND)
    message(STATUS "Found libssh via find_package")
    set(LIBSSH_TARGET ssh)
else()
    find_package(PkgConfig QUIET)
    if(PkgConfig_FOUND)
        pkg_check_modules(LIBSSH REQUIRED libssh)
        set(LIBSSH_TARGET "")
    else()
        message(FATAL_ERROR "libssh not found. Install via vcpkg or system package manager.")
    endif()
endif()

# nlohmann/json
find_package(nlohmann_json 3.0 QUIET CONFIG)
if(NOT nlohmann_json_FOUND)
    find_package(PkgConfig QUIET)
    if(PkgConfig_FOUND)
        pkg_check_modules(NLOHMANN_JSON nlohmann_json)
    endif()
    if(NLOHMANN_JSON_FOUND)
        set(NLOHMANN_JSON_TARGET "")
        set(NLOHMANN_JSON_INCLUDE ${NLOHMANN_JSON_INCLUDE_DIRS})
    else()
        find_path(NLOHMANN_JSON_INCLUDE_DIR nlohmann/json.hpp
            PATHS /opt/homebrew/include /usr/local/include /usr/include
        )
        if(NLOHMANN_JSON_INCLUDE_DIR)
            set(NLOHMANN_JSON_INCLUDE ${NLOHMANN_JSON_INCLUDE_DIR})
            set(NLOHMANN_JSON_TARGET "")
        else()
            message(FATAL_ERROR "nlohmann/json not found")
        endif()
    endif()
else()
    set(NLOHMANN_JSON_TARGET nlohmann_json::nlohmann_json)
    set(NLOHMANN_JSON_INCLUDE "")
endif()

# ============================================================================
# Qt Build
# ============================================================================
if(UI_TOOLKIT STREQUAL "Qt")
    set(CMAKE_AUTOMOC ON)
    set(CMAKE_AUTORCC ON)
    set(CMAKE_AUTOUIC ON)

    # Find Qt
    find_package(Qt6 QUIET COMPONENTS Core Widgets Network)
    if(NOT Qt6_FOUND)
        find_package(Qt5 REQUIRED COMPONENTS Core Widgets Network)
        set(QT_VERSION_MAJOR 5)
        message(STATUS "Using Qt5")
    else()
        set(QT_VERSION_MAJOR 6)
        message(STATUS "Using Qt6")
    endif()

    set(SOURCES
        ${COMMON_SOURCES}
        src/main_qt.cpp
        src/ui/qt/MainWindow.cpp
    )

    set(HEADERS
        ${COMMON_HEADERS}
        src/ui/qt/MainWindow.h
    )

    # Create executable
    if(WIN32)
        add_executable(${PROJECT_NAME} WIN32 ${SOURCES} ${HEADERS})
    elseif(APPLE)
        add_executable(${PROJECT_NAME} MACOSX_BUNDLE ${SOURCES} ${HEADERS})
    else()
        add_executable(${PROJECT_NAME} ${SOURCES} ${HEADERS})
    endif()

    # Link Qt
    if(QT_VERSION_MAJOR EQUAL 6)
        target_link_libraries(${PROJECT_NAME} PRIVATE Qt6::Core Qt6::Widgets Qt6::Network)
    else()
        target_link_libraries(${PROJECT_NAME} PRIVATE Qt5::Core Qt5::Widgets Qt5::Network)
    endif()

# ============================================================================
# FLTK Build
# ============================================================================
elseif(UI_TOOLKIT STREQUAL "FLTK")
    # Find FLTK
    find_package(FLTK QUIET CONFIG)
    if(FLTK_FOUND)
        message(STATUS "Found FLTK via find_package (CONFIG)")
        set(FLTK_TARGET fltk::fltk)
    else()
        find_package(PkgConfig QUIET)
        if(PkgConfig_FOUND)
            pkg_check_modules(FLTK fltk)
            if(FLTK_FOUND)
                message(STATUS "Found FLTK via pkg-config")
                set(FLTK_TARGET "")
            endif()
        endif()
        if(NOT FLTK_FOUND)
            find_package(FLTK REQUIRED)
            if(FLTK_FOUND)
                message(STATUS "Found FLTK via FindFLTK module")
                set(FLTK_TARGET "")
            endif()
        endif()
    endif()

    set(SOURCES
        ${COMMON_SOURCES}
        src/main_fltk.cpp
        src/ui/fltk/MainWindow.cpp
    )

    set(HEADERS
        ${COMMON_HEADERS}
        src/ui/fltk/MainWindow.h
    )

    # Create executable
    if(WIN32)
        add_executable(${PROJECT_NAME} WIN32 ${SOURCES} ${HEADERS})
    elseif(APPLE)
        add_executable(${PROJECT_NAME} MACOSX_BUNDLE ${SOURCES} ${HEADERS})
    else()
        add_executable(${PROJECT_NAME} ${SOURCES} ${HEADERS})
    endif()

    # Link FLTK
    if(FLTK_TARGET)
        target_link_libraries(${PROJECT_NAME} PRIVATE ${FLTK_TARGET})
    else()
        target_link_libraries(${PROJECT_NAME} PRIVATE ${FLTK_LIBRARIES})
        if(FLTK_LIBRARY_DIRS)
            target_link_directories(${PROJECT_NAME} PRIVATE ${FLTK_LIBRARY_DIRS})
        endif()
    endif()

    # Add FLTK include dirs
    if(NOT FLTK_TARGET AND FLTK_INCLUDE_DIRS)
        target_include_directories(${PROJECT_NAME} PRIVATE ${FLTK_INCLUDE_DIRS})
    endif()

else()
    message(FATAL_ERROR "Invalid UI_TOOLKIT: ${UI_TOOLKIT}. Must be 'Qt' or 'FLTK'")
endif()

# ============================================================================
# Common configuration for both builds
# ============================================================================

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Add libssh include dirs if using pkg-config
if(NOT libssh_FOUND AND LIBSSH_INCLUDE_DIRS)
    target_include_directories(${PROJECT_NAME} PRIVATE ${LIBSSH_INCLUDE_DIRS})
endif()

# Add nlohmann include dirs if needed
if(NLOHMANN_JSON_INCLUDE)
    target_include_directories(${PROJECT_NAME} PRIVATE ${NLOHMANN_JSON_INCLUDE})
endif()

# Link libssh
if(LIBSSH_TARGET)
    target_link_libraries(${PROJECT_NAME} PRIVATE ${LIBSSH_TARGET})
else()
    target_link_libraries(${PROJECT_NAME} PRIVATE ${LIBSSH_LIBRARIES})
    if(LIBSSH_LIBRARY_DIRS)
        target_link_directories(${PROJECT_NAME} PRIVATE ${LIBSSH_LIBRARY_DIRS})
    endif()
endif()

# Add nlohmann_json if using find_package
if(NLOHMANN_JSON_TARGET)
    target_link_libraries(${PROJECT_NAME} PRIVATE ${NLOHMANN_JSON_TARGET})
endif()

# Platform-specific settings
if(APPLE)
    set(MACOSX_BUNDLE_ICON_FILE app.icns)
    set(APP_ICON_MACOS "${CMAKE_CURRENT_SOURCE_DIR}/resources/icons/app.icns")
    if(EXISTS ${APP_ICON_MACOS})
        set_source_files_properties(${APP_ICON_MACOS} PROPERTIES
            MACOSX_PACKAGE_LOCATION "Resources")
        target_sources(${PROJECT_NAME} PRIVATE ${APP_ICON_MACOS})
    endif()
    set_target_properties(${PROJECT_NAME} PROPERTIES
        MACOSX_BUNDLE TRUE
        MACOSX_BUNDLE_BUNDLE_NAME "SSH Connector"
        MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
        MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION}
        MACOSX_BUNDLE_GUI_IDENTIFIER "com.sshconnector.app"
        MACOSX_BUNDLE_ICON_FILE app.icns
    )
    # Link Cocoa framework (needed for both Qt and FLTK on macOS)
    target_link_libraries(${PROJECT_NAME} PRIVATE "-framework Cocoa")
elseif(WIN32)
    set(APP_ICON_RESOURCE "${CMAKE_CURRENT_SOURCE_DIR}/resources/app.rc")
    if(EXISTS ${APP_ICON_RESOURCE})
        target_sources(${PROJECT_NAME} PRIVATE ${APP_ICON_RESOURCE})
    endif()
    target_link_libraries(${PROJECT_NAME} PRIVATE ws2_32)
    if(MSVC)
        target_compile_options(${PROJECT_NAME} PRIVATE
            $<$<CONFIG:Release>:/O1>
            $<$<CONFIG:Release>:/GL>
        )
        target_link_options(${PROJECT_NAME} PRIVATE
            $<$<CONFIG:Release>:/LTCG>
            $<$<CONFIG:Release>:/OPT:REF>
            $<$<CONFIG:Release>:/OPT:ICF>
        )
    endif()
else()
    # Linux
    find_package(Threads REQUIRED)
    target_link_libraries(${PROJECT_NAME} PRIVATE Threads::Threads)
    if(UI_TOOLKIT STREQUAL "FLTK")
        find_package(X11 REQUIRED)
        target_link_libraries(${PROJECT_NAME} PRIVATE ${X11_LIBRARIES})
    endif()
endif()

# Install rules
install(TARGETS ${PROJECT_NAME}
    BUNDLE DESTINATION .
    RUNTIME DESTINATION bin
)

if(UNIX AND NOT APPLE)
    install(FILES packaging/linux/ssh-connector.desktop
        DESTINATION share/applications)
endif()
