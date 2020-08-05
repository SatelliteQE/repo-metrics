Basic tooling for gathering specific metrics about GH prs.


Command structure:

`github-metrics` is the core command, with sub-commands to gather different types of metrics

`github-metrics gather prs`
This command with gather data related to PRs like comment times, average age of PRs.
Data will be arranged by PR.


`github-metrics gather reviewers`
This command with gather data related to reviewers activity like number of reviews in a time period.
Data will be arranged by reviewer


`github-metrics gather contributors`
This command with gather data related to contributors activity like number of opened PRs, merged PRs
Data will be arranged by repository
