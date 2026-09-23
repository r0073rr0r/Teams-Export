# Contributing to Teams-Export

Thanks for taking the time to contribute! 🎉

This is a small, focused tool for reading **your own** Microsoft Teams desktop cache on
**your own** machine. Contributions that keep it simple, local, and safe are very welcome.

## Ground rules

- **Scope.** This project only supports accessing data that belongs to you, on your own
  computer. Pull requests that add features for accessing other people's data, remote
  exfiltration, or bypassing another person's device or account will be rejected. See the
  [Code of Conduct](CODE_OF_CONDUCT.md).
- **License.** By contributing you agree that your contribution is licensed under the
  [GNU GPL-3.0](LICENSE).

## Getting started

```bash
git clone https://github.com/r0073rr0r/Teams-Export.git
cd Teams-Export
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python teams.py doctor
```

## Development workflow

1. Create a branch from `main`: `git checkout -b feature/my-change`.
2. Make your change. Keep it small and focused.
3. Run the tests and the linter locally — CI runs both on Python 3.10–3.13:
   ```bash
   pip install pytest "pylint==4.0.8"
   pytest -q
   pylint $(git ls-files '*.py')
   ```
   The build requires green tests and a clean lint (score 10/10 with the repo's `.pylintrc`).
4. **Never commit real data.** `export/`, cache copies (`*.ldb`, `*.log`, `*.leveldb/`),
   `teams_messages*.txt`, `teams_log*.jsonl` and `.env` are already git-ignored — please keep
   it that way. Test fixtures must be synthetic (made-up names, no real message content).
5. Open a pull request against `main` and fill in the template.

## Style

- Python 3.10+.
- Follow the existing style; the repo ships a `.pylintrc` that encodes it.
- Keep parsing of message content in `teamskit/render.py` as pure functions with tests.
  Only `teamskit/extract.py` touches the cache reader, and imports it lazily.

## When Teams changes its cache format

The tool depends on Microsoft-internal IndexedDB store and field names
(`Teams:replychain-manager`, `Teams:conversation-manager`, `Teams:profiles`). If an update
breaks the export, please open an issue with the Teams version and the (redacted) list of
database names — never paste message content.

## Reporting bugs / requesting features

Use the [issue templates](https://github.com/r0073rr0r/Teams-Export/issues/new/choose).
For anything security-related, follow the [Security Policy](SECURITY.md) instead of opening
a public issue.
