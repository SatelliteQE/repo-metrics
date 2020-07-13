import attr
from attrdict import AttrDict
from cached_property import cached_property
from github import Github

from config import settings


GH_repo = settings.gh_repo
GH_TOKEN = settings.gh_token

gh_api = Github(GH_TOKEN)

"""
Functions for interacting with github's API, calculating a PR's various timing metrics.
"""


class PullRequestMetrics(AttrDict):
    """Dummy class to provide distinct type around AttrDict"""

    pass


@attr.s
class PRWrapper(object):
    """Class for compositing additional properties onto the GH PR instance"""

    pr = attr.ib()  # the GH api PR object

    @cached_property
    def first_review(self):
        """When the first review on the PR occurred
        Returns None if there are no reviews
        """
        reviews_not_by_author = [
            review
            for review in self.pr.get_reviews()
            if review.user.login != self.pr.user.login
        ]
        reviews_not_by_author.sort(key=lambda r: r.submitted_at)
        return None if not reviews_not_by_author else reviews_not_by_author[0]

    @cached_property
    def review_label_added(self):
        """Determine when the review label was added"""
        events = [
            event
            for event in self.pr.get_issue_events()
            if (event.label and event.label.name == "review")
            and event.event == "labeled"
        ]
        return None if not events else events[0]

    @cached_property
    def create_to_first_review(self):
        """given a PR, calculate the time from its creation to the first review

        If the PR had a 'do not merge' label,
        use the time that the label was removed instead of when the PR was created

        Args:
            pr: a PRWrapper object
        """
        # days delta as float between pr created and first review
        # TODO factor in DO NOT MERGE label event
        if self.first_review is None:
            return None
        else:
            return (self.first_review.submitted_at - self.pr.created_at).total_seconds()

    @cached_property
    def review_label_to_first_review(self):
        """given a PR,
        calculate time from the review label being applied to when it got first review
        """
        if self.first_review is None or self.review_label_added is None:
            return None
        else:
            return (
                self.first_review.submitted_at - self.review_label_added.created_at
            ).total_seconds()


def time_to_comment(repo_name):
    """Iterate over the PRs in the repo and calculate times to the first comment

    Calculates the time delta per-PR from creation to comment, and from 'review' label to comment

    Args:
        repo_name: string repository name, including the owner/org (example: SatelliteQE/robottelo)

    Returns:
        dict, keyed on the PR number, where values are dictionaries containing timing metrics
    """
    repo = gh_api.get_repo(repo_name)
    prs = repo.get_pulls(state="open", sort="created", base="master")
    pr_metrics = dict()
    for pr in prs:
        pr = PRWrapper(pr)
        # TODO: multi-threaded processing of PRs

        pr_metrics[pr.pr.number] = PullRequestMetrics(
            create_to_review=pr.create_to_first_review,
            label_to_review=pr.review_label_to_first_review,
        )

    return pr_metrics


# for debugging purposes
if __name__ == "__main__":
    metrics = time_to_comment("SatelliteQE/robottelo")
