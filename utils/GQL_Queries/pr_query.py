# Importable strings for GQL queries
# Paginated on 50 PRs at a time

pr_review_query = """query getPRs($prCursor: String, $blockCount: Int = 50) {
  repository(owner:"SatelliteQE", name:"Robottelo") {
    pullRequests(
        first: $blockCount,
        after:  $prCursor
        orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        author {login}
        url
        createdAt
        isDraft
        timelineItems(first: 20, itemTypes: [PULL_REQUEST_REVIEW, PULL_REQUEST_REVIEW_THREAD, ISSUE_COMMENT, CONVERT_TO_DRAFT_EVENT, READY_FOR_REVIEW_EVENT]){
          totalCount
          nodes {
            ... on ConvertToDraftEvent {
              __typename
              createdAt
              actor {login}
            }
            ... on ReadyForReviewEvent {
              __typename
              createdAt
              actor {login}
            }
            ... on PullRequestReview {
              __typename
              author {login}
              state
              createdAt
              comments {totalCount}
            }
            ... on IssueComment {
              __typename
              author {login}
              createdAt
            }
          }
        }
      }
      pageInfo {endCursor}
    }
  }
}"""  # noqa
