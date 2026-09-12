# T025 — Round 10 review transport evidence

The connector and conditional authorization flow completed, but the response
could contain more than one structured review object during continuation. The
extractor previously selected the first object with verdict and review_context,
which could be an incomplete progress result before the evidence-complete
final result.

The extractor now selects the last matching review object. A regression test
covers an incomplete object followed by a complete object; empty or missing
changed-file lists remain invalid.
