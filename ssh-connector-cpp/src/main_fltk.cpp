#include "ui/fltk/MainWindow.h"

#include <FL/Fl.H>

int main(int argc, char* argv[])
{
    // Enable multithreading support for Fl::awake()
    Fl::lock();

    sshconn::MainWindow window;
    window.show(argc, argv);

    return Fl::run();
}
