from attrdict import AttrDict

from .GQL_Queries.github_wrappers import RepoWrapper

EMPTY = "---"

"""
Functions for collecting and organizing various timing metrics.

Metrics:
    - single_pr_metrics: review timing and content context about specific PRs
    - TODO: reviews_per_week: number of reviews per week for the last 4 weeks, average
    - TODO: reviews_per_user: number of reviews per user in the last week
    -
"""


class PullRequestMetrics(AttrDict):
    """Dummy class to provide distinct type around AttrDict"""

    pass


def single_pr_metrics(organization, repo_name, pr_count):
    """Iterate over the PRs in the repo and calculate times to the first comment

    Calculates the time delta per-PR from creation to comment, and from 'review' label to comment

    Args:
        organization: string organization or repository owner  (ex. SatelliteQE)
        repo_name: string repository name (ex. robottelo)

    Returns:
        dict, keyed on the PR number, where values are dictionaries containing timing metrics
    """
    # TODO rewrite with GQL data
    repo = RepoWrapper(organization, repo_name)
    pr_metrics = []
    for pr_num, pr in repo.pull_requests(count=pr_count).items():
        pr_metrics.append(
            {
                "PR": pr_num,
                "Author": pr.author,
                "State": pr.state,
                "Files": pr.changed_files,
                "Line Changes": f"+ {pr.additions} / - {pr.deletions}",
                "Hours to Comment": pr.hours_to_first_review or EMPTY,
                "Hours to Tier1": pr.hours_to_tier1 or EMPTY,
                "Hours to Tier2": pr.hours_to_tier2 or EMPTY,
                "Tier1 to Tier2": pr.hours_from_tier1_to_tier2 or EMPTY,
                "Non-Tier Reviewers": ", ".join(pr.reviews_by_non_tier) or EMPTY,
                "Tier1 Reviewers": ", ".join(
                    set([r.author for r in pr.reviews_by_tier1])
                ),
                "Tier2 Reviewers": ", ".join(
                    set([r.author for r in pr.reviews_by_tier2])
                ),
                "Merged By": pr.merged_by,
            }
        )

    pr_metrics.sort(key=lambda pr: pr["PR"])  # sort by pr number
    return pr_metrics


def reviewer_actions(org_name, team_slugs):
    """Collect metrics around reviewer activity on a given repo

    Gets list of members from GH organization teams.

    Organize metrics by:
        - given reviewer teams, and reviews by non-team members
        - within teams, number of reviews per reviewer
    """
    # Shriver: It might make sense to actually collect this data within time_to_Review
    # initial plan for implementation involved getting events from users
    # but those user events don't include PR comments

    # get a dictionary of team slug keys and member login lists
    # lots of API oddities to deal with here
    # There are reviews (approve, comment, reject) that have a body to them
    # There are review comments - comments made on the diff view
    # There are PR comments - comments made on the PR discussion page
    pass
