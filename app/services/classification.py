"""
Classification engine — deterministic rules first, AI fallback later.

Maps application names and domains to categories.
"""

from typing import Optional

# Application → Category mapping
APP_CLASSIFICATIONS: dict[str, tuple[str, bool]] = {
    # Coding (app_name_lower: (category, is_productive))
    "visual studio": ("Coding", True),
    "visual studio code": ("Coding", True),
    "code": ("Coding", True),
    "devenv": ("Coding", True),
    "rider": ("Coding", True),
    "intellij idea": ("Coding", True),
    "pycharm": ("Coding", True),
    "webstorm": ("Coding", True),
    "android studio": ("Coding", True),
    "xcode": ("Coding", True),
    "eclipse": ("Coding", True),
    "netbeans": ("Coding", True),
    "vim": ("Coding", True),
    "nvim": ("Coding", True),
    "neovim": ("Coding", True),
    "emacs": ("Coding", True),
    "sublime text": ("Coding", True),
    "atom": ("Coding", True),
    "notepad++": ("Coding", True),
    "cursor": ("Coding", True),
    # DSA
    "leetcode": ("DSA", True),
    # Terminals
    "terminal": ("Coding", True),
    "windows terminal": ("Coding", True),
    "cmd": ("Coding", True),
    "powershell": ("Coding", True),
    "bash": ("Coding", True),
    "wsl": ("Coding", True),
    "iterm": ("Coding", True),
    "hyper": ("Coding", True),
    # Databases
    "dbeaver": ("Work", True),
    "datagrip": ("Work", True),
    "pgadmin": ("Work", True),
    "tableplus": ("Work", True),
    "sequel pro": ("Work", True),
    # Communication
    "slack": ("Communication", True),
    "teams": ("Communication", True),
    "microsoft teams": ("Communication", True),
    "discord": ("Communication", False),  # can be distraction
    "zoom": ("Meeting", True),
    "google meet": ("Meeting", True),
    "skype": ("Meeting", True),
    "outlook": ("Communication", True),
    "thunderbird": ("Communication", True),
    # Entertainment
    "spotify": ("Entertainment", False),
    "vlc": ("Entertainment", False),
    "netflix": ("Entertainment", False),
    "youtube": ("Entertainment", False),
    "twitch": ("Entertainment", False),
    "steam": ("Gaming", False),
    "epic games": ("Gaming", False),
    # Office / Work
    "word": ("Work", True),
    "excel": ("Work", True),
    "powerpoint": ("Work", True),
    "onenote": ("Study", True),
    "notion": ("Work", True),
    "obsidian": ("Study", True),
    "typora": ("Study", True),
    # Design
    "figma": ("Work", True),
    "sketch": ("Work", True),
    "photoshop": ("Work", True),
    "illustrator": ("Work", True),
    "affinity designer": ("Work", True),
    # Browsers (generic — domain-level will refine)
    "chrome": ("Other", False),
    "firefox": ("Other", False),
    "edge": ("Other", False),
    "safari": ("Other", False),
    "brave": ("Other", False),
    "opera": ("Other", False),
}

# Domain → Category mapping
DOMAIN_CLASSIFICATIONS: dict[str, tuple[str, bool]] = {
    # Coding / Dev
    "github.com": ("Coding", True),
    "gitlab.com": ("Coding", True),
    "bitbucket.org": ("Coding", True),
    "stackoverflow.com": ("Study", True),
    "developer.mozilla.org": ("Study", True),
    "docs.python.org": ("Study", True),
    "docs.microsoft.com": ("Study", True),
    "learn.microsoft.com": ("Study", True),
    "reactjs.org": ("Study", True),
    "vuejs.org": ("Study", True),
    "npmjs.com": ("Coding", True),
    "pypi.org": ("Coding", True),
    "crates.io": ("Coding", True),
    "codepen.io": ("Coding", True),
    # DSA
    "leetcode.com": ("DSA", True),
    "hackerrank.com": ("DSA", True),
    "codeforces.com": ("DSA", True),
    "topcoder.com": ("DSA", True),
    "exercism.org": ("DSA", True),
    "adventofcode.com": ("DSA", True),
    # Study / Learning
    "coursera.org": ("Study", True),
    "udemy.com": ("Study", True),
    "edx.org": ("Study", True),
    "khanacademy.org": ("Study", True),
    "pluralsight.com": ("Study", True),
    "linkedin.com/learning": ("Study", True),
    "youtube.com/watch": ("Study", False),  # ambiguous — could be study or not
    "medium.com": ("Study", True),
    "dev.to": ("Study", True),
    "hashnode.com": ("Study", True),
    # Work / Productivity
    "notion.so": ("Work", True),
    "trello.com": ("Work", True),
    "asana.com": ("Work", True),
    "linear.app": ("Work", True),
    "jira.atlassian.com": ("Work", True),
    "clickup.com": ("Work", True),
    "figma.com": ("Work", True),
    "miro.com": ("Work", True),
    # Communication
    "mail.google.com": ("Communication", True),
    "outlook.office.com": ("Communication", True),
    "slack.com": ("Communication", True),
    "discord.com": ("Communication", False),
    "teams.microsoft.com": ("Meeting", True),
    "zoom.us": ("Meeting", True),
    "meet.google.com": ("Meeting", True),
    # Entertainment
    "youtube.com": ("Entertainment", False),
    "netflix.com": ("Entertainment", False),
    "twitch.tv": ("Entertainment", False),
    "hulu.com": ("Entertainment", False),
    "primevideo.com": ("Entertainment", False),
    "disneyplus.com": ("Entertainment", False),
    "9gag.com": ("Entertainment", False),
    "reddit.com": ("Social", False),
    # Social
    "twitter.com": ("Social", False),
    "x.com": ("Social", False),
    "facebook.com": ("Social", False),
    "instagram.com": ("Social", False),
    "tiktok.com": ("Social", False),
    "linkedin.com": ("Work", True),  # professional
    "whatsapp.com": ("Communication", False),
    # Gaming
    "store.steampowered.com": ("Gaming", False),
    "epicgames.com": ("Gaming", False),
}


def classify_application(app_name: Optional[str]) -> tuple[str, bool]:
    """Return (category, is_productive) for a given application name."""
    if not app_name:
        return ("Other", False)
    lower = app_name.lower().strip()
    # Exact match first
    if lower in APP_CLASSIFICATIONS:
        return APP_CLASSIFICATIONS[lower]
    # Partial match
    for key, value in APP_CLASSIFICATIONS.items():
        if key in lower or lower in key:
            return value
    return ("Other", False)


def classify_domain(domain: Optional[str]) -> tuple[str, bool]:
    """Return (category, is_productive) for a given domain."""
    if not domain:
        return ("Other", False)
    lower = domain.lower().strip().removeprefix("www.")
    if lower in DOMAIN_CLASSIFICATIONS:
        return DOMAIN_CLASSIFICATIONS[lower]
    # Suffix match (e.g. subdomain)
    for key, value in DOMAIN_CLASSIFICATIONS.items():
        if lower.endswith(key) or key.endswith(lower):
            return value
    return ("Other", False)


def classify(
    app_name: Optional[str] = None,
    domain: Optional[str] = None,
    source: str = "desktop",
) -> tuple[str, bool]:
    """Classify an activity to (category, is_productive)."""
    if source == "browser" and domain:
        return classify_domain(domain)
    if app_name:
        cat, prod = classify_application(app_name)
        # If browser application and domain known, refine
        if cat == "Other" and domain:
            return classify_domain(domain)
        return cat, prod
    return ("Other", False)
