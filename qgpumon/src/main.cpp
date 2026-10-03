#include <QApplication>
#include <QLabel>

int main(int argc, char **argv)
{
    QCoreApplication::setOrganizationName(QStringLiteral("GPUMonitor"));
    QApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("GPU Monitor"));
    app.setStyle(QStringLiteral("Fusion"));

    QLabel w(QStringLiteral("qgpumon scaffold"));
    w.resize(400, 200);
    w.show();
    return app.exec();
}
