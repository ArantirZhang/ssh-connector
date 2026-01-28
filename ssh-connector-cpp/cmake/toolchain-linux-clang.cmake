# CMake Toolchain File for Cross-Compiling to Linux x64 using Clang
#
# Usage:
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/toolchain-linux-clang.cmake \
#         -DQT_HOST_PATH=/opt/homebrew/opt/qt@6 ..
#
# Prerequisites:
#   - LLVM/Clang with multi-target support (brew install llvm lld)
#   - Linux sysroot at /opt/linux-sysroot with:
#     - glibc, libstdc++, and system headers
#     - Qt6, libssh, nlohmann-json development packages
#   - Qt6 for Linux at /opt/qt6-linux (optional, for static Qt6 builds)

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

# Find Homebrew LLVM (Apple's Clang doesn't support cross-compilation)
set(LLVM_PREFIX "/opt/homebrew/opt/llvm" CACHE PATH "Path to Homebrew LLVM")

find_program(LLVM_CLANG clang
    PATHS ${LLVM_PREFIX}/bin
    NO_DEFAULT_PATH
    REQUIRED
)
find_program(LLVM_CLANGXX clang++
    PATHS ${LLVM_PREFIX}/bin
    NO_DEFAULT_PATH
    REQUIRED
)
find_program(LLVM_LLD ld.lld
    PATHS ${LLVM_PREFIX}/bin
    NO_DEFAULT_PATH
    REQUIRED
)

set(CMAKE_C_COMPILER ${LLVM_CLANG})
set(CMAKE_CXX_COMPILER ${LLVM_CLANGXX})

# Target triple for x86_64 Linux with GNU ABI
set(CMAKE_C_COMPILER_TARGET x86_64-linux-gnu)
set(CMAKE_CXX_COMPILER_TARGET x86_64-linux-gnu)

# Sysroot paths
set(LINUX_SYSROOT "/opt/linux-sysroot" CACHE PATH "Path to Linux cross-compile sysroot")
set(QT6_LINUX_PATH "/opt/qt6-linux" CACHE PATH "Path to Qt6 Linux installation")

set(CMAKE_SYSROOT ${LINUX_SYSROOT})

# Search paths for libraries and headers
set(CMAKE_FIND_ROOT_PATH
    ${LINUX_SYSROOT}
    ${QT6_LINUX_PATH}
)

# Search behavior
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Use LLD linker for cross-compilation
set(CMAKE_EXE_LINKER_FLAGS_INIT "-fuse-ld=lld")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "-fuse-ld=lld")

# Qt6 host path (required for moc, rcc, uic)
if(NOT DEFINED QT_HOST_PATH AND DEFINED ENV{QT_HOST_PATH})
    set(QT_HOST_PATH "$ENV{QT_HOST_PATH}" CACHE PATH "Path to host Qt installation")
endif()

# Additional compiler flags for cross-compilation
set(CMAKE_C_FLAGS_INIT "--target=x86_64-linux-gnu")
set(CMAKE_CXX_FLAGS_INIT "--target=x86_64-linux-gnu")
