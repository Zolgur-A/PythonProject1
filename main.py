from __future__ import annotations

import logging
import sys

from app.service import build_service
from app.ui_server import run_ui


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
UI_ARGUMENT = "--ui"


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def main() -> None:
    configure_logging()
    if UI_ARGUMENT in sys.argv:
        run_ui()
        return
    service = build_service()
    service.run()


if __name__ == "__main__":
    main()
