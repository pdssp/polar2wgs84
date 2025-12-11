# skeleton-python-binary -  Command-line tool that generates project templates based on predefined Python project template
# Copyright (C) 2024-2025 - Centre National d'Etudes Spatiales
# SPDX-License-Identifier: Apache-2.0
"""
Module to configure global application logging using Loguru.

This module provides a function to set up a global logger using the `loguru` library,
allowing customization of log levels, output destinations, and formatting options.
"""
import sys

from loguru import logger


def configure_logging(level="INFO", sink=sys.stderr, **kwargs):
    """
    Configure a global loguru logger.
    """
    logger.remove()
    logger.add(sink, level=level.upper(), **kwargs)
