# Rewrite boundary

This commit replaces the active PowerPack implementation with a clean delivery architecture.

The entire pre-rewrite repository tree is preserved under backup/ in the same commit, in addition to normal Git history.

Active product artifacts must not import, load, execute or resolve templates/state from the archive. Useful code or ideas may be copied into active paths and are then independently maintained.
