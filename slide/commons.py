PATTERN_COMPOSITE_PROFILE = r"(?i)perfil\s*composto"  # Matches "perfil composto" with any spacing
PATTERN_CONVENTIONAL_PROFILE = r"(?i)perfil\s*convencional"  # Matches "perfil convencional" with any spacing
PATTERN_PROFILES = r"(?i)perfil\s*(composto|convencional)"  # Matches "perfil composto" or "perfil convencional" with any spacing
PATTERN_MD5_CATALOG = r"(?i)^md5.*\.txt$"
PATTERNS = [PATTERN_MD5_CATALOG]

BAR_FORMAT = "{desc:<}\n{bar} {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"