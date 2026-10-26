# GO anaStruct v0.5.8-preview — section mapping popup UX

Read-only GO Factory Gable / Core nominal steel section integration inherited from
v0.5.7-preview. Solver/worker and numerical models remain unchanged.

## Fix

Previously: an input dialog and a yes/no warning were displayed for each
unique steel section. Pressing No then triggered a *second* warning that the
import was cancelled, even though cancel was a legitimate choice.

Now: section chooser remains one per unseen section/axis, followed by
**one consolidated** summary confirmation for all new choices. No/Cancel
leaves the previous analytical model untouched without a separate warning.
Accepted mappings are cached in the saved model as before; they are reused
only if the pinned Core catalog SHA-256 is unchanged.

## Test on IngeTrazo 0.5.9

Run RUN_V058_SECTION_UX_WINDOWS.cmd from this feature branch to validate
source and produce the ZIP. Close IngeTrazo, run
install_preview_058_windows.cmd, and cold-restart.

1. On first Factory 01 import, choose H-300x300x10x15 Strong and WF-300x150
   Strong; one combined confirmation should appear.
2. Click **No**. Model should remain unchanged; no second warning.
3. Repeat, click **Yes**; the Gable frame should load.
4. Re-import or switch Y station. Same catalog/mapping should not prompt.
5. Change Core SHA source or choose a different catalog. Consent must not be
   silently reused; source mismatch blocks import for review.
6. Inspect Loads, Combinations, Releases, Pin/Fixed and old worker results.

**Preview only, no physical manufacturer's section verification.**
