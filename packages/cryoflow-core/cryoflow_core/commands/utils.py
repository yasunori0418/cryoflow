import logging


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI.

    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(levelname)s: %(message)s',
        level=level,
    )
