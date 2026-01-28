cmake_minimum_required(VERSION 3.16)
project(ssh-connector VERSION 1.0.0 LANGUAGES CXX)

# Cross-compilation support
if(CMAKE_CROSSCOMPILING)
    message(STATUS "Cross-compiling for ${CMAKE_SYSTEM_NAME} (${CMAKE_SYSTEM_PROCESSOR})")

    # QT_HOST_PATH is required for Qt's moc, rcc, uic tools when cross-compiling
    if(NOT DEFINED QT_HOST_PATH AND NOT DEFINED ENV{QT_HOST_PATH})
        message(FATAL_ERROR
            "QT_HOST_PATH must be set for cross-compilation.\n"
            "Set via -DQT_HOST_PATH=... or export QT_HOST_PATH=...\n"
            "Example: export QT_HOST_PATH=/opt/homebrew/opt/qt@6"
        )
    endif()

    # Use environment variable if CMake variable not set
    if(DEFINED ENV{QT_HOST_PATH} AND NOT DEFINED QT_HOST_PATH)
        set(QT_HOST_PATH "$ENV{QT_HOST_PATH}" CACHE PATH "Path to host Qt installation")
    endif()

    message(STATUS "Using host Qt from: ${QT_HOST_PATH}")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Find Qt - prefer Qt6, fallback to Qt5
find_package(Qt6 QUIET COMPONENTS Core Widgets Network)
if(NOT Qt6_FOUND)
    find_package(Qt5 REQUIRED COMPONENTS Core Widgets Network)
    set(QT_VERSION_MAJOR 5)
    message(STATUS "Using Qt5")
else()
    set(QT_VERSION_MAJOR 6)
    message(STATUS "Using Qt6")
endif()

# Find libssh - try find_package first (vcpkg), then pkg-config
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

# nlohmann/json - header-only (try find_package first, fallback to pkg-config)
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
        # Try system include path
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

# Source files
set(SOURCES
    src/main.cpp
    src/config/Config.cpp
    src/config/ConfigManager.cpp
    src/core/SSHClient.cpp
    src/core/TunnelHandler.cpp
    src/ui/MainWindow.cpp
)

set(HEADERS
    src/config/Config.h
    src/config/ConfigManager.h
    src/core/ConnectionState.h
    src/core/SSHClient.h
    src/core/TunnelHandler.h
    src/ui/MainWindow.h
)

# Platform-specific resources
if(WIN32)
    set(APP_ICON_RESOURCE "${CMAKE_CURRENT_SOURCE_DIR}/resources/app.rc")
    list(APPEND SOURCES ${APP_ICON_RESOURCE})
endif()

# Create executable
add_executable(${PROJECT_NAME} ${SOURCES} ${HEADERS})

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

# Link libraries
if(QT_VERSION_MAJOR EQUAL 6)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        Qt6::Core
        Qt6::Widgets
        Qt6::Network
    )
else()
    target_link_libraries(${PROJECT_NAME} PRIVATE
        Qt5::Core
        Qt5::Widgets
        Qt5::Network
    )
endif()

# Link libssh
if(LIBSSH_TARGET)
    target_link_libraries(${PROJECT_NAME} PRIVATE ${LIBSSH_TARGET})
else()
    target_link_libraries(${PROJECT_NAME} PRIVATE ${LIBSSH_LIBRARIES})
    target_link_directories(${PROJECT_NAME} PRIVATE ${LIBSSH_LIBRARY_DIRS})
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
elseif(WIN32)
    set_target_properties(${PROJECT_NAME} PROPERTIES
        WIN32_EXECUTABLE TRUE
    )
    # Optimize for size in Release builds
    if(MSVC)
        target_compile_options(${PROJECT_NAME} PRIVATE
            $<$<CONFIG:Release>:/O1>      # Optimize for size
            $<$<CONFIG:Release>:/GL>      # Whole program optimization
        )
        target_link_options(${PROJECT_NAME} PRIVATE
            $<$<CONFIG:Release>:/LTCG>    # Link-time code generation
            $<$<CONFIG:Release>:/OPT:REF> # Remove unreferenced code
            $<$<CONFIG:Release>:/OPT:ICF> # Identical COMDAT folding
        )
    endif()
endif()

# Install rules
install(TARGETS ${PROJECT_NAME}
    BUNDLE DESTINATION .
    RUNTIME DESTINATION bin
)

# Linux desktop file installation
if(UNIX AND NOT APPLE)
    install(FILES packaging/linux/ssh-connector.desktop
        DESTINATION share/applications)
endif()
