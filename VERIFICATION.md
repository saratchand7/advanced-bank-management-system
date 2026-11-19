# Verification record

## Original Windows author evidence

- Original source submission: `f00aacca83fa96f38a375cc1c6ad73b262ca4adf`, 16 November 2026 (India).
- Environment: Windows, Python 3.12.9. The application uses only the Python standard library.
- `python -m unittest discover -s tests -v`: 21 tests passed.
- `python tools/smoke_test.py`: all 14 menu choices, statement export and restart balance assertions passed.
- `python -m compileall .`: passed.

These are the original executed checks, retained as author evidence rather than represented as a new run.

## Review correction submission

- Review: `PFS_Advanced_Bank_Fresher_Review_f00aacc.txt`, dated 18 November 2026 (India).
- Corrected implementation commit: `d3c0dbc02beb0d1dadad2b1fa1035402dcf85155`.
- Correction and verification date: 19 November 2026 (India).
- Environment: Windows, Python 3.12.9.
- This evidence accompanies the implementation above in a following documentation-only commit. Resolve the final submission with `git rev-parse HEAD` or the repository commit history.

### Executed checks on the corrected code

| Command | Executed result |
| --- | --- |
| `python -m unittest discover -s tests -v` | 32 discovered: 31 passed, 1 explicitly skipped, no failures or errors |
| `python tools/smoke_test.py` | Passed all 14 menu choices, safe statement export and restart assertions |
| `python -m compileall .` | Passed |
| `git diff --check` | Passed |

The final unittest run used ordinary Windows account permissions outside the filesystem sandbox so the real hard-link regression could run. The symbolic-link regression was skipped because Windows returned WinError 1314 (the account lacks symbolic-link creation privilege). No symbolic-link test pass is claimed. The initial sandbox run skipped both link tests; the final run above supersedes that result and successfully exercised a real hard link.

### Export regression evidence

- Export to the active snapshot is rejected with ValidationError. Original snapshot bytes remain identical.
- Absolute, relative, dot/parent-component and Windows case-equivalent snapshot paths cannot bypass protection.
- A real hard link to the snapshot is rejected and both files retain their original bytes.
- Existing unrelated TXT files and prior statement exports are not overwritten.
- Default exports create different filenames under the active data directory's `statements/` folder.
- New explicit absolute/relative TXT destinations succeed and bank restart still loads the same balances and ledger.
- The CLI rejects the snapshot and an existing notes file, then successfully exports with a blank destination in the same session.
- Invalid extensions, unknown accounts and write permission failures produce the expected banking errors.
- Existing transfer rollback, restart, corrupted-ledger and interest-duplicate checks still pass.

These results are from executed tests. Symbolic-link behavior remains a platform-skipped check; it can run on a system that already permits creating symbolic links. No OS privilege changes are required to use the application.

## Data and scope

Tests use disposable temporary directories and do not touch customer data. Default runtime snapshots, statement exports, ZIP packages, caches and local presentation files are excluded from Git. No new banking features, frameworks or storage layers were added. The existing atomic snapshot and transfer rollback design remains in place.

See README.md for clone/setup instructions, application commands, export restrictions, architecture, assumptions and limitations.
