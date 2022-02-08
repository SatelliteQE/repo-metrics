# Importable string for GQL query

org_team_members_query = """query orgTeamMembers($organization: String!, $team: String!) {
    organization(login:$organization) {
        team(slug:$team) {
            name
            members{
                nodes {
                    login
                    name
                }
            }
        }
    }
}
"""  # noqa: E501

contributions_counts_by_user_query = """query getContributions($user: String! $from_date: DateTime!, $to_date: DateTime!) {
  user(login:$user) {
    contributionsCollection (from:$from_date, to: $to_date) {
        pullRequestContributionsByRepository {
        repository {name}
        contributions { totalCount }
      }
      pullRequestReviewContributionsByRepository {
        repository {name}
        contributions { totalCount }

      }
      issueContributionsByRepository {
        repository {name}
        contributions {totalCount}
      }
      commitContributionsByRepository {
        repository {name}
        contributions {totalCount}
      }
    }
  }
}
"""  # noqa: E501

contributions_by_org_members_query = """query getContributions ($organization: String!, $team: String!, $from_date: DateTime!, $to_date: DateTime!) {
  organization(login:$organization) {
    team(slug:$team) {
      name
      members {
        nodes {
          login
          contributionsCollection (from: $from_date, to: $to_date) {
              pullRequestContributionsByRepository (maxRepositories:10) {
                    repository {name}
              contributions (last:10){
                nodes {
                  pullRequest {
                    number
                    changedFiles
                    deletions
                    additions
                  }
                  occurredAt
                }
              }
            }
            pullRequestReviewContributionsByRepository (maxRepositories: 10) {
              repository {name}
              contributions (last:50) {
                nodes {
                  occurredAt
                  pullRequest { number }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""  # noqa: E501

contributions_counts_by_org_members_query = """
query contributions_counts_by_org_members_query ($organization: String!, $team: String!, $from_date: DateTime!, $to_date: DateTime!) {
    organization(login: $organization) {
        team(slug: $team) {
            name
            members {
                nodes {
                    login
                    contributionsCollection (from: $from_date, to: $to_date) {
                        pullRequestContributionsByRepository {
                            repository {name}
                            contributions { totalCount }
                        }
                        pullRequestReviewContributionsByRepository {
                            repository {name}
                            contributions { totalCount }

                        }
                        issueContributionsByRepository {
                            repository {name}
                            contributions {totalCount}
                        }
                        commitContributionsByRepository {
                            repository {name}
                            contributions {totalCount}
                        }
                    }
                }
            }
        }
    }
}
"""  # noqa: E501
