# Importable strings for GQL queries

org_teams_query = """query getReviewerTeams($organization: String!) {
  organization(login:$organization) {
  	teams (first:100){
      nodes {
        name
        members {
          nodes {
            login
          }
        }
      }
    }
  }
}"""  # noqa
