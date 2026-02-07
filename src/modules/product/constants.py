"""Product module constants — IMPA code patterns and extension code configuration."""

import re

IMPA_CODE_PATTERN = r"^(\d{6}|EXT-\d{6})$"
IMPA_CODE_REGEX = re.compile(IMPA_CODE_PATTERN)

EXTENSION_CODE_PREFIX = "EXT-"

# IMPA prefix is the first 2 digits of a 6-digit IMPA code
IMPA_PREFIX_LENGTH = 2

# Maximum length of an IMPA code (EXT-XXXXXX = 10 chars)
IMPA_CODE_MAX_LENGTH = 10
