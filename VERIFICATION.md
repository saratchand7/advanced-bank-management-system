# Verification record

Environment: Windows, Python 3.12.9. The application uses the Python standard library only.

- `python -m unittest discover -s tests -v`: 21 tests passed.
- `python tools/smoke_test.py`: all 14 menu choices, statement export and restart balance assertions passed.
- `python -m compileall .`: passed.

Tests use temporary directories. Runtime customer records, ZIP packages, caches and local presentation files are excluded from Git.

See README.md for application commands, architecture, assumptions and limitations.
