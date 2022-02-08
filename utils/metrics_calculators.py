from collections import defaultdict
from datetime import date
from datetime import datetime
from datetime import timedelta
from statistics import fmean
from statistics import median
from statistics import pstdev

from box import Box
from dateutil.rrule import rrule
from dateutil.rrule import WEEKLY

from .GQL_Queries.github_wrappers import RepoWrapper
from .GQL_Queries.github_wrappers import UserWrapper

EMPTY = "---"

DATE_FMT = "%y-%m-%d"

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


class PullRequestMetrics(Box):
    """Dummy class to provide distinct type around Box"""

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
    t1_by_week = defaultdict(lambda: defaultdict(int))
    for reviewer, actions in tier1_actions.items():
        for action in actions:
            t1_by_week[action[0].isocalendar()[0:2]][reviewer] += 1

    t2_by_week = defaultdict(lambda: defaultdict(int))
    for reviewer, actions in tier2_actions.items():
        for action in actions:
            t2_by_week[action[0].isocalendar()[0:2]][reviewer] += 1

    t1_metrics = []
    for week, actions in t1_by_week.items():
        t1_metrics.append(
            {
                "Week": f"{date.fromisocalendar(week[0], week[1], 1).strftime(DATE_FMT)} to "
                f"{date.fromisocalendar(week[0], week[1], 7)}",
                **actions,
            }
        )
    t2_metrics = []
    for week, actions in t2_by_week.items():
        t2_metrics.append(
            {
                "Week": f"{date.fromisocalendar(week[0], week[1], 1).strftime(DATE_FMT)} to "
                f"{date.fromisocalendar(week[0], week[1], 7)}",
                **actions,
            }
        )

    t1_metrics.sort(key=lambda m: m["Week"], reverse=True)
    t2_metrics.sort(key=lambda m: m["Week"], reverse=True)
    return t1_metrics, t2_metrics


def contributor_actions(user, num_weeks):
    """
    Gather metrics for contributions by week for members of an organization team

    Query will include PR, issue, PR review, and commit contributions by repository, by week

    Iterate over weekly recurrance queries

    Data returned is ready for tabulate with headers=keys
    Organize metrics by type of action, first column is week, finally by repository
    """
    userwrap = UserWrapper(login=user)
    dated_counts = defaultdict(list)
    now = datetime.now()
    starting_date = now - timedelta(weeks=num_weeks)
    # rrule will create a list of start/stop times for weekly interval
    datelist = rrule(WEEKLY, until=now, dtstart=starting_date)
    # iterate over sets of start/stop by zipping the list against itself
    # relying on python to keep these list items in order.
    for from_date, to_date in zip(datelist, datelist[1:]):

        user_contributions = userwrap.contributions(
            from_date=from_date, to_date=to_date
        )
        # {'pullRequest': {'repo-metrics': 1},
        #  'pullRequestReview': {'robottelo': 1},
        #  'issue': {},
        #  'commit': {}

        # want:
        # {'week': [from0, from1, from2]
        #  'pullRequest': [{'repo': 1}, {}, {'other': 2}]}

        dated_counts["week"].append(from_date.strftime(DATE_FMT))

        for cont_type, cont_repos in user_contributions.items():
            # Convert the raw value dicts to table cell values
            if cont_repos:
                dated_counts[cont_type].append(
                    "\n".join(f"{r}: {c}" for r, c in cont_repos.items())
                )
            else:
                dated_counts[cont_type].append("---")

    return dated_counts
