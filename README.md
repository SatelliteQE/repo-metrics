Basic tooling for gathering specific metrics about GH prs.

# Configuration and Installation
1. Clone the repository to your local filesystem, and create a python 3.7+ virtualenv to run in.
2. Copy `settings.yaml.example` to `settings.yaml` and modify as you need for your metrics collection.
3. A GitHub API token needs to be generated and set in `settings.yaml` as `gh_token`. It needs read permissions.
4. Reviewer teams need to be defined to classify tier1, tier2 reviews. This tool assumes you use a two tier review process.
5. `pip install -e .` in your new virtualenv, which will install the `github-metrics` command.


# Command structure

`github-metrics` is the core command, with sub-commands to gather different types of metrics

`github-metrics pr-report`
This command with gather data related to PRs like comment times, average age of PRs.
Data will be arranged by PR.


`github-metrics reviewer-report`
This command with gather data related to reviewers activity like number of reviews in a time period.
Data will be arranged by reviewer

`--help` is available for both commands, to see available options and their description.

# Common command options

`--output-file-prefix`
Prepends the output files, formatted in html tables, with the given string.  Can be set in settings.yaml

`--repo`
Defines the repository to scan for metrics.
Can be provided multiple times, separate reports will be generated for each repository

`--org`
Defines the GitHub organization where the given repository exists

`--pr-count`
Defines the number of PRs to include in the scan for reporting. Will collect PRs from the latest by number.
