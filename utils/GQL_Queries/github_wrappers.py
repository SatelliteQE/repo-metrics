from datetime import datetime

import attr
from cached_property import cached_property
from gql import Client as gql_client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport
from logzero import logger

from config import settings
from utils.GQL_Queries.pr_query import pr_review_query
from utils.GQL_Queries.review_teams_query import org_teams_query


GH_TOKEN = settings.gh_token
GH_GQL_URL = "https://api.github.com/graphql"
GH_TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

SECONDS_TO_HOURS = 3600


@attr.s
class RepoWrapper:
    """Class to wrap PRs within a repo, fetching PR data via GQL"""

    organization = attr.ib()
    repo_name = attr.ib()

    GQL_TX = RequestsHTTPTransport(
        url=GH_GQL_URL, headers={"Authorization": f"bearer {GH_TOKEN}"}
    )
    GH_CLIENT = gql_client(transport=GQL_TX, fetch_schema_from_transport=True)

    def pull_requests(self, count=100, block_count=100):
        """dictionary of PRWrapper instances, keyed on PR numbers
        Args:
            count (Int): total number of PRs fetched
            block_count(Int): number of PRs to fetch in each query, GH gql limits to 100
        """
        # gql query grabs blocks of 50 PRs at a time
        if block_count > count:
            block_count = count
        pr_nodes = []
        fetched = 0  # tracks total number of PRs pulled
        gql_pr_cursor = None
        while fetched < count:
            pr_block = self.GH_CLIENT.execute(
                gql(pr_review_query),
                variable_values={"prCursor": gql_pr_cursor, "blockCount": block_count},
            )
            gql_pr_cursor = pr_block["repository"]["pullRequests"]["pageInfo"][
                "endCursor"
            ]
            pr_nodes.extend(pr_block["repository"]["pullRequests"]["nodes"])
            fetched += block_count
        prws = {}
        # flatten data_blocks a bit, we just want the nodes
        for pr_node in pr_nodes:
            pr_num = pr_node["url"].split("/")[-1]

            if pr_node["author"]["login"] == "pyup-bot":
                continue  # ignore pyup PRs

            # wrap timeline events first
            # maybe move the events into a PRWrapper property
            events = []
            for e in pr_node["timelineItems"]["nodes"]:
                if e.get("author", {}).get("login") == "codecov":
                    continue  # ignore codecov comments
                event_class = EVENT_CLASS_MAP[e.pop("__typename")]
                if e.get("author") or e.get("actor"):
                    # some events use actor instead of author, standardize it
                    e["author"] = (
                        e.pop("author", {}).get("login") or e.pop("actor")["login"]
                    )
                if e.get("createdAt"):
                    # just change the camel to underscore formatting
                    e["created_at"] = e.pop("createdAt")
                events.append(event_class(**e))

            prws[int(pr_num)] = PRWrapper(
                number=pr_num,
                repo=self,
                url=pr_node["url"],
                author=pr_node["author"]["login"],
                created_at=pr_node["createdAt"],
                is_draft=pr_node["isDraft"],
                timeline_events=events,
                merged_by=(pr_node["mergedBy"] or {}).pop("login", None),
                changed_files=pr_node["changedFiles"],
                state=pr_node["state"],
                additions=pr_node["additions"],
                deletions=pr_node["deletions"],
            )
        return prws

    @cached_property
    def reviewer_teams(self):
        """Look up teams on the org, compare to settings file for tier1/tier2 teams

        Returns:
            dictionary, keyed on 'tier1' and 'tier2', with lists of team members
        """
        org_teams = self.GH_CLIENT.execute(
            gql(org_teams_query), variable_values={"organization": self.organization},
        )["organization"]["teams"]["nodes"]
        try:
            settings_team_names = settings.reviewer_teams.get(self.organization).get(
                self.repo_name
            )
            tier_1_team = [
                t for t in org_teams if t["name"] == settings_team_names.tier1
            ][0]
            tier_2_team = [
                t for t in org_teams if t["name"] == settings_team_names.tier2
            ][0]
            return {
                "tier1": [m["login"] for m in tier_1_team["members"]["nodes"]],
                "tier2": [m["login"] for m in tier_2_team["members"]["nodes"]],
            }
        except Exception:
            logger.error(
                "Reviewer teams have not been entered in settings.yaml, "
                "or did not match teams on the organization."
                f"[{self.organization}] teams from GitHub: "
                f'{[t.get("name") for t in org_teams]}'
            )
            import sys

            sys.exit(1)


@attr.s
class EventWrapper:
    """Class for modeling the events in GH"""

    author = attr.ib()
    created_at = attr.ib(converter=lambda t: datetime.strptime(t, GH_TS_FMT))


@attr.s
class PRCommentWrapper(EventWrapper):
    pass


@attr.s
class PRReviewWrapper(EventWrapper):
    state = attr.ib()
    comments = attr.ib()


@attr.s
class DraftWrapper(EventWrapper):
    pass


@attr.s
class ReadyWrapper(EventWrapper):
    pass  # same attrs as draft


EVENT_CLASS_MAP = dict(
    IssueComment=PRCommentWrapper,
    PullRequestReview=PRReviewWrapper,
    ConvertToDraftEvent=DraftWrapper,
    ReadyForReviewEvent=ReadyWrapper,
)


@attr.s
class PRWrapper:
    """Class for modeling the data returned from the GQL query for PRs"""

    number = attr.ib()
    repo = attr.ib()
    url = attr.ib()
    created_at = attr.ib(converter=lambda t: datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ"))
    author = attr.ib()
    timeline_events = attr.ib()
    is_draft = attr.ib()
    state = attr.ib()
    changed_files = attr.ib()
    merged_by = attr.ib()
    additions = attr.ib()
    deletions = attr.ib()

    def __repr__(self):
        return (
            f'[{self.url.split("/")[-1]}] by {self.author}, '
            f"review events: {len(self.timeline_events)}"
        )

    @cached_property
    def reviews_and_comments(self):
        """Collects reviews and PR comments, sorted by creation date"""
        review_events = filter(
            lambda e: isinstance(e, (PRReviewWrapper, PRCommentWrapper)),
            self.timeline_events,
        )
        events_not_by_author = [
            review for review in review_events if review.author != self.author
        ]
        events_not_by_author.sort(key=lambda r: r.created_at)
        return events_not_by_author

    @cached_property
    def reviews_by_tier1(self):
        if not self.reviews_and_comments:
            return []
        return [
            review
            for review in self.reviews_and_comments
            if review.author in self.repo.reviewer_teams["tier1"]
        ]

    @cached_property
    def reviews_by_tier2(self):
        if not self.reviews_and_comments:
            return []
        return [
            review
            for review in self.reviews_and_comments
            if review.author in self.repo.reviewer_teams["tier2"]
        ]

    @cached_property
    def reviews_by_non_tier(self):
        return list(
            set([r.author for r in self.reviews_and_comments])
            - (
                set([r.author for r in self.reviews_by_tier1])
                | set([r.author for r in self.reviews_by_tier2])
            )
        )

    @cached_property
    def first_review(self):
        """When the first review on the PR occurred
        Sorts the reviews not by the author, oldest first
        Returns None if there are no reviews
        """
        return None if not self.reviews_and_comments else self.reviews_and_comments[0]

    @cached_property
    def second_review(self):
        """When the first review on the PR occurred
        Sorts the reviews not by the author, oldest first
        Returns None if there are no reviews
        """
        return (
            None if len(self.reviews_and_comments) < 2 else self.reviews_and_comments[1]
        )

    @cached_property
    def ready_for_review(self):
        """Determine when the PR entered ready_for_review state

        This could happen multiple times in a PR's lifecycle, so return a list of events
        Sort events by creation date, oldest first

        Returns:
            list of ReadyWrapper instances
        """
        # don't want a generator here, wrapping with list explicitly
        ready_events = list(
            filter(lambda e: isinstance(e, ReadyWrapper), self.timeline_events)
        )
        ready_events.sort(key=lambda e: e.created_at)
        return ready_events or [
            ReadyWrapper(
                author=self.author, created_at=self.created_at.strftime(GH_TS_FMT)
            )
        ]

    @cached_property
    def comment_comparison_date(self):
        # if there were comments before a 'ready for review' event, use PR creation
        if self.first_review.created_at > self.ready_for_review[0].created_at:
            comparison_date = self.ready_for_review[0].created_at
        else:
            comparison_date = self.created_at
        return comparison_date

    @cached_property
    def hours_to_first_review(self):
        """calculate the time from being ready for review to the first review or comment

        Few things to account for here
        0. No reviews yet
        1. PR opened in ready state, no events present for draft/ready
        2. PR opened in draft state, event for ready
        3. PR is still in draft state, value is N/A
        4. PR has multiple draft/ready state events

        In case #4, we need to look at whether there are any comments/reviews and
        look at the first review against the closest ready event

        Args:
            pr: a PRWrapper object
        """
        # case 0, no review yet or case 3, PR in draft state
        if self.first_review is None or self.is_draft:
            return None

        # case 2, use event for draft state
        # case 1, use creation date
        # both handled by self.ready_for_review
        # if there were comments before a 'ready for review' event, use PR creation
        return round(
            (
                self.first_review.created_at - self.comment_comparison_date
            ).total_seconds()
            / SECONDS_TO_HOURS,
            1,
        )

    @cached_property
    def hours_to_tier1(self):
        if not self.reviews_by_tier1:
            return None
        return round(
            (
                self.reviews_by_tier1[0].created_at - self.comment_comparison_date
            ).total_seconds()
            / SECONDS_TO_HOURS,
            1,
        )

    @cached_property
    def hours_to_tier2(self):
        """Calculate the time to the first approved tier2 review"""
        if not self.reviews_by_tier2:
            return None
        return round(
            (
                self.reviews_by_tier2[0].created_at - self.comment_comparison_date
            ).total_seconds()
            / SECONDS_TO_HOURS,
            1,
        )

    @cached_property
    def hours_from_tier1_to_tier2(self):
        """This has some problems - if there is no approved tier1 review, this doesn't mean much
        If there was no tier1 review at all, it means nothing
        """
        approved_reviews = [
            r for r in self.reviews_by_tier1 if getattr(r, "state", None) == "APPROVED"
        ]
        if not approved_reviews or not self.reviews_by_tier2:
            return None
        return round(
            (
                self.reviews_by_tier2[0].created_at - approved_reviews[0].created_at
            ).total_seconds()
            / SECONDS_TO_HOURS,
            1,
        )
