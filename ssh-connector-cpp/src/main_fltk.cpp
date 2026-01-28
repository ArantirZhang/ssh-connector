#include "ui/fltk/MainWindow.h"
#include "config/ConfigManager.h"

#include <FL/Fl.H>
#include <filesystem>

int main(int argc, char* argv[])
{
    // Set executable directory for portable key search
    if (argc > 0 && argv[0]) {
        std::filesystem::path exePath(argv[0]);
        sshconn::ConfigManager::setExecutableDir(exePath.parent_path().string());
    }

    // Enable multithreading support for Fl::awake()
    Fl::lock();

    sshconn::MainWindow window;
    window.show(argc, argv);

    return Fl::run();
}
