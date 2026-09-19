# Independent review

Independent code review runs only after Spec Kit convergence stabilizes and the feature branch has been committed, pushed and represented by exactly one open Pull Request.

The reviewer must use the configured GitHub App as repository evidence, bind the exact PR head to local full HEAD, cover every changed file and requirement, continue after the first finding, revalidate prior findings and challenge its tentative verdict.

Review outputs are stored under .specify/powerpack/delivery/reviews/.

CHANGES_REQUIRED is mandatory work. After remediation, Spec Kit converge runs again before the next review. BLOCKED never becomes approval.
