from attrdict import AttrDict

from .GQL_Queries.github_wrappers import RepoWrapper
from config import settings


GH_repo = settings.gh_repo
GH_TOKEN = settings.gh_token

SECONDS_TO_DAYS = 86400


"""
Functions for interacting with github's API, calculating a PR's various timing metrics.

Metrics:
    - time_to_comment: how long from PR creation/ready-for-review state to the first review, per pr
    - TODO: time_from_first_to_second: how long from first approval to second review, average
    - TODO: time_from_review_to_ready: how long from a rejected review to ready state, average
    - TODO: reviews_per_week: number of reviews per week for the last 4 weeks, average
    - TODO: reviews_per_user: number of reviews per user in the last week
    -
"""


class PullRequestMetrics(AttrDict):
    """Dummy class to provide distinct type around AttrDict"""

    pass


def time_to_review(organization, repo_name, pr_count):
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
    pr_metrics = [
        (pr_num, round(pr.hours_to_first_review, 1), pr.author, pr.first_review.author)
        for pr_num, pr in repo.pull_requests(count=pr_count).items()
        if pr.hours_to_first_review is not None
    ]

    pr_metrics.sort(key=lambda tup: tup[1])  # sort by hours
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
