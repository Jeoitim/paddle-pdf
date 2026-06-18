"""Allow running as `python -m paddle_pdf`."""

import sys

from .controller.cli_controller import main

sys.exit(main())
