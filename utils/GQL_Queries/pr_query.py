# Importable strings for GQL queries

pr_review_query = """query {
  repository(owner:"SatelliteQE", name:"Robottelo") {
    pullRequests(first: 10, orderBy: {field: CREATED_AT, direction: DESC}) {
      edges{
        node {
          author {login}
          url
          createdAt
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
      					author: author {login}
                createdAt
              }
            }
          }
        }
      }
    }
  }
}"""  # noqa
