from collections import defaultdict
from statistics import fmean
from statistics import median
from statistics import pstdev

from attrdict import AttrDict

from .GQL_Queries.github_wrappers import RepoWrapper

EMPTY = "---"

HEADER_H_COM = "Hours to Comment"
HEADER_H_T1 = "Hours to Tier1"
HEADER_H_T2 = "Hours to Tier2"

STAT_HEADERS = {
    "fmean": "Mean",
    "median": "Median",
    "pstdev": "Pop. Standard Deviation",
}

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


def single_pr_metrics(organization, repository, pr_count=100):
    """Iterate over the PRs in the repo and calculate times to the first comment

    Calculates the time delta per-PR from creation to comment, and from 'review' label to comment

    Args:
        organization: string organization or repository owner  (ex. SatelliteQE)
        repo_name: string repository name (ex. robottelo)

    Returns:
        tuple of
        dict, keyed on the PR number, where values are dictionaries containing timing metrics
        dict, keyed with table headers, of statistical values

    """
    repo = RepoWrapper(organization, repository)
    pr_metrics = []
    for pr in repo.pull_requests(count=pr_count).values():
        pr_state = pr.state
        if pr_state == "OPEN":
            pr_state = f"{pr_state}{' - DRAFT' if pr.is_draft else ''}"
        pr_metrics.append(
            {
                "PR": pr.number,
                "Author": pr.author,
                "State": pr_state,
                "Files": pr.changed_files,
                "Line Changes": f"+ {pr.additions} / - {pr.deletions}",
                HEADER_H_COM: pr.hours_to_first_review or EMPTY,
                HEADER_H_T1: pr.hours_to_tier1 or EMPTY,
                HEADER_H_T2: pr.hours_to_tier2 or EMPTY,
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

    # calculate some column averages
    hours_to_comment = [p[HEADER_H_COM] for p in pr_metrics if p[HEADER_H_COM] != EMPTY]
    hours_to_tier1 = [p[HEADER_H_T1] for p in pr_metrics if p[HEADER_H_T1] != EMPTY]
    hours_to_tier2 = [p[HEADER_H_T2] for p in pr_metrics if p[HEADER_H_T2] != EMPTY]
    stat_metrics = []
    for stat in [fmean, median, pstdev]:
        stat_metrics.append(
            {
                "Metric": STAT_HEADERS[stat.__name__],
                HEADER_H_COM: stat(hours_to_comment),
                HEADER_H_T1: stat(hours_to_tier1),
                HEADER_H_T2: stat(hours_to_tier2),
            }
        )

    pr_metrics.sort(key=lambda n: n["PR"], reverse=True)  # sort by pr number
    return pr_metrics, stat_metrics


def reviewer_actions(organization, repository, pr_count=100):
    """Collect metrics around reviewer activity in a given organization

    Gets list of members from GH organization teams, pulled from config

    Organize metrics by:
        - given reviewer teams, and reviews by non-team members
        - within teams, number of reviews per reviewer
    """
    repo = RepoWrapper(organization, repository)
    team_actions = repo.reviewer_team_actions(pr_count=pr_count)
    tier1_actions = team_actions.pop("tier1")
    tier2_actions = team_actions.pop("tier2")

    # split actions into weekly blocks to show review/comment actions over time
    # want to create list of dictionaries
    # first item is the week
    # columns are individuals with count of reviews in that week

    # go through t1 actions, create new dict keyed by tuple of year,week
    t1_by_week = {}
    for reviewer, actions in tier1_actions.items():
        for action in actions:
            date_tuple = action[0].isocalendar()[0:2]
            if date_tuple not in t1_by_week:
                t1_by_week[date_tuple] = defaultdict(int)
            t1_by_week[date_tuple][reviewer] += 1

    t2_by_week = {}
    for reviewer, actions in tier2_actions.items():
        for action in actions:
            date_tuple = action[0].isocalendar()[0:2]
            if date_tuple not in t2_by_week:
                t2_by_week[date_tuple] = defaultdict(int)
            t2_by_week[date_tuple][reviewer] += 1

    t1_metrics = []
    for week, actions in t1_by_week.items():
        t1_metrics.append({"Week": str(week), **actions})
    t2_metrics = []
    for week, actions in t2_by_week.items():
        t2_metrics.append({"Week": str(week), **actions})

    t1_metrics.sort(key=lambda m: m["Week"], reverse=True)
    t2_metrics.sort(key=lambda m: m["Week"], reverse=True)
    return t1_metrics, t2_metrics
