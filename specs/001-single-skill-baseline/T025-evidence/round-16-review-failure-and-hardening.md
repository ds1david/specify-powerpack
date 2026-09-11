# T025 — Round 16 review transport evidence

The first review stream invoked a connector/tool and reached an explicit
authorization gate. The final allow continuation completed without another
tool marker, and the transport overwrote the global invocation list with that
last empty list. The review client then incorrectly rejected the conversation
as having no connector evidence.

The transport now accumulates tool invocations across the initial stream and
all same-conversation allow continuations before returning the review turn.
