PATTERN_COMPOSITE_PROFILE = r"perfil\s*composto"  # Matches "perfil composto" with any spacing
PATTERN_CONVENTIONAL_PROFILE = r"perfil\s*convencional"  # Matches "perfil convencional" with any spacing
PATTERN_MD5_CATALOG = r"^md5.*\.txt$"
PATTERNS = [PATTERN_MD5_CATALOG]

BAR_FORMAT = "{desc:<}\n{bar} {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"