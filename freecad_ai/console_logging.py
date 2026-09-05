"""Route addon logs to FreeCAD's report view with their original severity."""

import logging


class FreeCADConsoleHandler(logging.Handler):
    """Use the native console API, including from MCP worker threads."""

    def __init__(self, console):
        super().__init__()
        self.console = console
        self.setFormatter(logging.Formatter("%(name)s: %(message)s"))

    def emit(self, record):
        try:
            message = self.format(record).rstrip("\n") + "\n"
            if record.levelno >= logging.ERROR:
                self.console.PrintError(message)
            elif record.levelno >= logging.WARNING:
                self.console.PrintWarning(message)
            else:
                self.console.PrintMessage(message)
        except Exception:
            self.handleError(record)


def configure_console_logging(console):
    """Install once for GUI entry points, leaving other addons' logging alone.

    FreeCAD renders stderr as errors regardless of a Python record's level.
    Stop propagation to root stderr handlers; retain explicitly installed
    addon handlers and levels. Importing this module has no effect on stdio.
    """
    logger = logging.getLogger("freecad_ai")
    for handler in logger.handlers:
        if isinstance(handler, FreeCADConsoleHandler):
            handler.console = console
            break
    else:
        logger.addHandler(FreeCADConsoleHandler(console))
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)
    logger.propagate = False
