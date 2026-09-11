# T025 — Round 13 review transport evidence

The first response in the same review contained a valid four-entry
path-keyed changed-file map. The evidence-completion continuation returned a
complete context but replaced the file set with an empty list.

The runner now retains the previously proven non-empty file set when a same-
segment continuation omits or empties it, while taking immutable SHAs from the
completion response. No file path is invented; the retained paths originated
in the GitHub connector response.
