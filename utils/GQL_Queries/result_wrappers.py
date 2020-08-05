from datetime import datetime

import attr
from cached_property import cached_property
from gql import Client as gql_client
from gql import gql
from gql import RequestsHTTPTransport

from config import settings
from utils.GQL_Queries.pr_query import pr_review_query


GH_TOKEN = settings.gh_token
GH_GQL_URL = "https://api.github.com/graphql"
GH_TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

SECONDS_TO_DAYS = 86400


@attr.s
class RepoWrapper(object):
    """Class to wrap PRs within a repo, fetching PR data via GQL"""

    organization = attr.ib()
    repo_name = attr.ib()

    GQL_TX = RequestsHTTPTransport(
        url=GH_GQL_URL, headers={"Authorization": f"bearer {GH_TOKEN}"}
    )
    GH_CLIENT = gql_client(transport=GQL_TX, fetch_schema_from_transport=True)

    @cached_property
    def pull_requests(self):
        """dictionary of PRWrapper instances, keyed on PR numbers"""
        data = self.GH_CLIENT.execute(gql(pr_review_query))
        prws = {}
        for pr in data["repository"]["pullRequests"]["edges"]:
            pr_num = pr["node"]["url"].split("/")[-1]

            # wrap timeline events first
            events = []
            for e in pr["node"]["timelineItems"]["nodes"]:
                if e.get("author", {}).get("login") == "codecov":
                    continue  # ignore codecov comments
                events.append(EVENT_CLASS_MAP[e.pop("__typename")](**e))

            prws[int(pr_num)] = PRWrapper(
                url=pr["node"]["url"],
                author=pr["node"]["author"]["login"],
                created_at=pr["node"]["createdAt"],
                timeline_events=events,
            )
        return prws


@attr.s
class EventWrapper(object):
    """Class for modeling the events in GH"""

    createdAt = attr.ib(converter=lambda t: datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ"))


@attr.s
class PRCommentWrapper(EventWrapper):
    author = attr.ib()


@attr.s
class PRReviewWrapper(EventWrapper):
    author = attr.ib()
    state = attr.ib()
    comments = attr.ib()


@attr.s
class DraftWrapper(EventWrapper):
    actor = attr.ib()


@attr.s
class ReadyWrapper(DraftWrapper):
    pass  # same attrs as draft


EVENT_CLASS_MAP = dict(
    IssueComment=PRCommentWrapper,
    PullRequestReview=PRReviewWrapper,
    ConvertToDraftEvent=DraftWrapper,
    ReadyForReviewEvent=ReadyWrapper,
)


@attr.s
class PRWrapper(object):
    """Class for modeling the data returned from the GQL query for PRs"""

    url = attr.ib()
    created_at = attr.ib(converter=lambda t: datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ"))
    author = attr.ib()
    timeline_events = attr.ib()

    def __str__(self):
        return f'[{self.url.split("/")[-1]}] by {self.author}, review events: {len(self.timeline_events)}'

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
            return (
                self.first_review.submitted_at - self.pr.created_at
            ).total_seconds() / SECONDS_TO_DAYS

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
            ).total_seconds() / SECONDS_TO_DAYS
