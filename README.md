<h1 align="center">📤 Teams-Export</h1>

<p align="center">
    Read and export <strong>your own</strong> Microsoft Teams chat history on
    <strong>your own</strong> Windows computer — into a clean, readable chronological log.
    No login, no API, no admin consent; it reads the new Teams app's local cache.
</p>

<p align="center">
    <a href="https://github.com/r0073rr0r/Teams-Export/actions/workflows/tests.yml"><img src="https://github.com/r0073rr0r/Teams-Export/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
    <a href="https://github.com/r0073rr0r/Teams-Export/actions/workflows/pylint.yml"><img src="https://github.com/r0073rr0r/Teams-Export/actions/workflows/pylint.yml/badge.svg" alt="Pylint"></a>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/r0073rr0r/Teams-Export" alt="License: GPL-3.0"></a>
    <img src="https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white" alt="Platform: Windows">
    <a href="https://github.com/r0073rr0r/Teams-Export/commits/main"><img src="https://img.shields.io/github/last-commit/r0073rr0r/Teams-Export" alt="Last commit"></a>
    <a href="https://github.com/r0073rr0r/Teams-Export/issues"><img src="https://img.shields.io/github/issues/r0073rr0r/Teams-Export" alt="Issues"></a>
    <a href="https://github.com/r0073rr0r/Teams-Export/stargazers"><img src="https://img.shields.io/github/stars/r0073rr0r/Teams-Export?style=social" alt="GitHub Stars"></a>
</p>

> [!IMPORTANT]
> **Purpose and boundaries.** Strictly for accessing **your own** data on **your own**
> machine (backup, migration, personal archive). Not for other people's devices or
> accounts. Everything runs locally; nothing is sent anywhere.

---

## 🤔 Why

- **Teams for personal use** (a private Microsoft account, teams.live.com) has no export
  and no Graph API access for third-party tools — Microsoft 365 connectors only accept
  work/school accounts.
- **Work accounts** without a Teams licence, or tenants that block app consent, leave you
  with the same problem.

In both cases the messages are already on your disk: the new Teams app caches them locally.
This tool reads that cache.

## 🧠 How it works (short version)

The new Teams app (MSTeams, Teams 2.x) is a WebView2 application. Each signed-in account type
gets its own browser profile, and the chat data lives in that profile's **IndexedDB**
(a LevelDB folder, Snappy-compressed, values in V8 serialization):

| Profile | Folder | Account |
|---|---|---|
| `personal` | `WV2Profile_tfl` | private Microsoft account (teams.live.com) |
| `work` | `WV2Profile_tfw` | work/school account (teams.microsoft.com) |

under `%LOCALAPPDATA%\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\Microsoft\MSTeams\EBWebView\`.

1. **Snapshot** — the LevelDB folder is copied into `export/_snapshot/` (the `LOCK` file is
   skipped), so Teams can keep running and the original is never touched.
2. **Extract** — [`ccl_chromium_reader`](https://github.com/cclgroupltd/ccl_chromium_reader)
   decodes the snapshot. Three stores are read:
   - `Teams:replychain-manager` / `replychains` — the messages,
   - `Teams:conversation-manager` / `conversations` — chat and group names,
   - `Teams:profiles` / `profiles` — display names.
3. **Render** — HTML bodies, reply quotes, emoji, files, photos, voice messages, polls and
   call events are flattened to plain text. A pending local copy and the server copy of the
   same message are merged (by `clientMessageId`).

## 📦 Requirements

- Windows, **Python 3.10+**
- The **new Microsoft Teams** app (MSTeams) installed and signed in at least once
- `pip install -r requirements.txt`
  - `ccl_chromium_reader` — IndexedDB/LevelDB reader (not on PyPI, installed from GitHub)
  - `python-snappy` — Snappy decompression

## ⚙️ Setup

1. `pip install -r requirements.txt`
   — or install it as a package to get the `teams-export` command:
   ```bash
   pip install .            # then use:  teams-export export
   ```
2. Check: `python teams.py doctor`

> [!NOTE]
> Everything under `export/` is in `.gitignore` — **your data never goes to GitHub.**

## 🚀 Usage

```bash
python teams.py export                             # RECOMMENDED: both profiles, everything in the cache
python teams.py export --since 2026-09-22T21:00    # only messages from a given local time
python teams.py export --profile personal          # only the private-account profile
```

> If you installed it as a package (see [Setup](#️-setup)), use `teams-export export`
> instead of `python teams.py export`.

Output:
- `export/teams_messages.txt` — a readable chronological log (text, reply quotes, files,
  photos, voice messages, polls, calls, edits, reactions)
- `export/teams_log.jsonl` — the same log as structured JSON, one message per line (ideal for
  feeding to an AI)
- `export/_snapshot/` — the copy of the cache that was read

Log format:

```
[2026-09-23 14:11:33] IN  Alice Example: text                  1:1, received
[2026-09-23 14:07:05] OUT -> Alice Example: text               1:1, sent
[2026-09-23 13:59:46] IN  [Project Team] Bob Example: text     group chat
    continuation lines of a multi-line message are indented
```

A reply shows the quoted message first, prefixed with `> `. `(edited)` marks an edited
message, `[👍2 ❤️1]` a reaction summary (reactions with no known emoji show as `(name)`).

## 🧰 All methods

| Command | What it does | Needs Teams running? |
|---|---|:---:|
| `export` | snapshot the cache and build the log **(recommended)** | ❌ |
| `doctor` | environment check (install, cache sizes, dependencies) | ❌ |

## 🔄 What if I close or update Teams?

- **Teams closed:** `export` still works — it reads the cache on disk. But the cache only
  receives new messages **while Teams runs**, so for the latest messages keep Teams open for
  a while (or start it) before exporting.
- **Only what Teams has synced is there.** Old chats you never opened on this machine may be
  incomplete.
- **Teams update:** the store and field names are Microsoft-internal. If an update breaks the
  export (e.g. `0 messages`), check the database names inside the snapshot and open an issue.
- The export is a **point-in-time snapshot**. For the latest messages, run `export` again.

## 🗂️ Structure

```
teams.py            # CLI (all commands)
teamskit/           # logic
  config.py           paths (Teams profiles, outputs to export/)
  snapshot.py         copy the live LevelDB into export/_snapshot/
  extract.py          read messages/chats/names from the snapshot, de-duplicate
  render.py           message content -> text (HTML, quotes, files, calls)  [pure, tested]
  output.py           .txt + .jsonl writer, --since filter
tests/              # pytest unit tests on synthetic samples
export/             # your data (gitignored, empty in the repo)
```

## 🩺 Troubleshooting

- **`Teams app dir ... NOT found`** — only the new Teams (MSTeams) is supported, not classic
  Teams 1.x.
- **`cache: (empty / not found)` for a profile** — that account type was never signed in on
  this machine. A work account without a Teams licence also stays empty.
- **`0 messages`** — Teams changed its cache format; see [Contributing](CONTRIBUTING.md#when-teams-changes-its-cache-format).
- **Latest messages missing** — start Teams, let it sync, run `export` again.
- **Garbled characters in the console** — run with `PYTHONIOENCODING=utf-8`; the files
  themselves are always UTF-8.

## 🙏 Credits

Decoding of Chromium IndexedDB/LevelDB is done by
[ccl_chromium_reader](https://github.com/cclgroupltd/ccl_chromium_reader) by CCL Solutions
Group (MIT License).

## 🤝 Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md) first. CI runs the tests and lints on Python 3.10–3.13
and requires a clean `pylint` run (10/10) with the repo's [`.pylintrc`](.pylintrc).

## 🔐 Security

Found a vulnerability? Please **do not** open a public issue — follow the
[Security Policy](SECURITY.md) to report it privately.

## ⚖️ Legal & License

This tool only accesses a local cache that belongs to you, on your own machine. You are
responsible for using it in accordance with local laws, your employer's policies and
Microsoft's terms. Do not use it on data that is not yours.

Licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE).

<p align="center"><sub>Made with ❤️ by <a href="https://github.com/r0073rr0r">r0073rr0r</a></sub></p>
