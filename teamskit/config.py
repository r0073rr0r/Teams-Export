"""Paths for the new Microsoft Teams (MSTeams / Teams 2.x) desktop app on Windows."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(ROOT, "export")
SNAPSHOT_DIR = os.path.join(EXPORT_DIR, "_snapshot")

EBWEBVIEW = os.path.expandvars(
    r"%LOCALAPPDATA%\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\Microsoft\MSTeams\EBWebView")

# One WebView2 profile per account type:
#   personal  -> WV2Profile_tfl  (Teams "free", teams.live.com, private Microsoft account)
#   work      -> WV2Profile_tfw  (work/school account, teams.microsoft.com)
PROFILES = {
    "personal": ("WV2Profile_tfl", "https_teams.live.com_0"),
    "work": ("WV2Profile_tfw", "https_teams.microsoft.com_0"),
}


def leveldb_dir(profile):
    folder, origin = PROFILES[profile]
    return os.path.join(EBWEBVIEW, folder, "IndexedDB", origin + ".indexeddb.leveldb")


def snapshot_dir(profile):
    return os.path.join(SNAPSHOT_DIR, profile, os.path.basename(leveldb_dir(profile)))
