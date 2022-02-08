from datetime import datetime
from pathlib import Path

import click
from tabulate import multiline_formats
from tabulate import tabulate

from config import METRICS_OUTPUT
from config import settings
from utils import file_io
from utils import metrics_calculators
from utils.GQL_Queries.github_wrappers import OrgWrapper


# keys that will be read from settings files (dynaconf parsing) for command input defaults
SETTINGS_OUTPUT_PREFIX = "output_file_prefix"
SETTINGS_REVIEWER_TEAMS = "reviewer_teams"


# parent click group for report and graph commands
@click.group()
def report():
    pass


# reused options for multiple metrics functions
# TODO read defaults from settings
output_prefix_option = click.option(
    "--output-file-prefix",
    default=settings.get(SETTINGS_OUTPUT_PREFIX, "metrics-report"),
    help="Will only take file name (with or without extension), but not a full path."
    "Will append the metric name an epoch timestamp to the file name.",
)
org_name_option = click.option(
    "--org",
    default="SatelliteQE",
    help="The organization or user, for review counts across multiple repos",
)
repo_name_option = click.option(
    "--repo",
    default=["robottelo"],
    multiple=True,
    help="The repository name, like robottelo. ",
)
team_name_option = click.option(
    "--team",
    default=[],
    multiple=True,
    help="The github team name slug (URL field form, like quality-engineers)",
)
user_name_option = click.option(
    "--user",
    default=[],
    multiple=True,
    help="The github login name (URL field form, like mshriver)",
)
pr_count_option = click.option(
    "--pr-count",
    default=50,
    help="Number of PRs to include in metrics counts, will start from most recently created",
)
num_weeks_option = click.option(
    "--num-weeks",
    default=4,
    type=click.IntRange(1, 52),
    help="Number of weeks of metrics history to collect",
)
table_format_option = click.option(
    "--table-format",
    default="fancy_grid",
    type=click.Choice(multiline_formats),
    help="The tabulate output format, https://github.com/astanin/python-tabulate#multiline-cells",
)


@report.command(
    "pr-report",
    help="Gather metrics about individual PRs for a GH repo (SatelliteQE/robottelo)",
)
@org_name_option
@repo_name_option
@output_prefix_option
@pr_count_option
@table_format_option
def repo_pr_metrics(org, repo, output_file_prefix, pr_count, table_format):
    for repo_name in repo:
        click.echo(f"Collecting metrics for {org}/{repo_name} ...")

        pr_metrics, stat_metrics = metrics_calculators.single_pr_metrics(
            organization=org, repository=repo_name, pr_count=pr_count
        )

        header = f"Review Metrics By PR for [{repo_name}]"
        click.echo(f"\n{'-' * len(header)}")
        click.echo(header)
        click.echo("-" * len(header))
        click.echo(
            tabulate(pr_metrics, headers="keys", tablefmt=table_format, floatfmt=".1f")
        )

        header = f"Review Metric Statistics for [{repo_name}]"
        click.echo(f"\n{'-' * len(header)}")
        click.echo(header)
        click.echo("-" * len(header))
        click.echo(
            tabulate(
                stat_metrics, headers="keys", tablefmt=table_format, floatfmt=".1f"
            )
        )

        pr_metrics_filename = METRICS_OUTPUT.joinpath(
            f"{Path(output_file_prefix).stem}-"
            f"{org}-"
            f"{repo_name}-"
            "pr_metrics-"
            f"{datetime.now().isoformat(timespec='minutes')}.html"
        )
        click.echo(f"\nWriting PR metrics as HTML to {pr_metrics_filename}")
        file_io.write_to_output(
            pr_metrics_filename,
            tabulate(pr_metrics, headers="keys", tablefmt="html", floatfmt=".1f"),
        )

        stat_metrics_filename = METRICS_OUTPUT.joinpath(
            f"{Path(output_file_prefix).stem}-"
            f"{org}-"
            f"{repo_name}-"
            "stat_metrics-"
            f"{datetime.now().isoformat(timespec='minutes')}.html"
        )
        click.echo(f"\nWriting statistics metrics as HTML to {stat_metrics_filename}")
        file_io.write_to_output(
            stat_metrics_filename,
            tabulate(stat_metrics, headers="keys", tablefmt="html", floatfmt=".1f"),
        )


@report.command(
    "reviewer-report", help="Gather metrics on reviewer actions within a GH repo"
)
@org_name_option
@repo_name_option
@output_prefix_option
@pr_count_option
@table_format_option
def reviewer_actions(org, repo, output_file_prefix, pr_count, table_format):
    """ Generate metrics for tier reviewer groups, and general contributors

    Will collect tier reviewer teams from the github org
    Tier reviewer teams will read from settings file, and default to what SatelliteQE uses

    """
    for repo_name in repo:
        click.echo(f"Collecting metrics for {org}/{repo_name} ...")

        t1_metrics, t2_metrics = metrics_calculators.reviewer_actions(
            organization=org, repository=repo_name, pr_count=pr_count
        )
        header = f"Tier1 Reviewer actions by week for [{repo_name}]"
        click.echo(f"\n{'-' * len(header)}")
        click.echo(header)
        click.echo("-" * len(header))
        click.echo(tabulate(t1_metrics, headers="keys", tablefmt=table_format))

        header = f"Tier2 Reviewer actions by week for [{repo_name}]"
        click.echo(f"\n{'-' * len(header)}")
        click.echo(header)
        click.echo("-" * len(header))
        click.echo(tabulate(t2_metrics, headers="keys", tablefmt=table_format))

        tier1_metrics_filename = METRICS_OUTPUT.joinpath(
            f"{Path(output_file_prefix).stem}-"
            f"{org}-"
            f"{repo_name}-"
            "tier1_reviewers-"
            f"{datetime.now().isoformat(timespec='minutes')}.html"
        )
        click.echo(f"\nWriting PR metrics as HTML to {tier1_metrics_filename}")
        file_io.write_to_output(
            tier1_metrics_filename,
            tabulate(t1_metrics, headers="keys", tablefmt="html"),
        )

        tier2_metrics_filename = METRICS_OUTPUT.joinpath(
            f"{Path(output_file_prefix).stem}-"
            f"{org}-"
            f"{repo_name}-"
            "tier2_reviewers-"
            f"{datetime.now().isoformat(timespec='minutes')}.html"
        )
        click.echo(f"\nWriting PR metrics as HTML to {tier2_metrics_filename}")
        file_io.write_to_output(
            tier2_metrics_filename,
            tabulate(t2_metrics, headers="keys", tablefmt="html"),
        )


@report.command("contributor-report")
@org_name_option
@output_prefix_option
@team_name_option
@num_weeks_option
@table_format_option
@user_name_option
def contributor_actions(org, output_file_prefix, team, num_weeks, table_format, user):
    """Collect count metrics of various contribution types"""

    orgwrap = OrgWrapper(name=org)

    collected_users = []

    if not (user or team):
        click.echo("ERROR: Need to specify either a team and/or user")

    collaborators = list(user)  # might be empty, we're gonna add users from the team(s)

    for team_name in team:
        # Assert the team exists and list its members
        team_members = orgwrap.team_members(team=team_name)
        click.echo(f"Team members for {org}/{team_name}:\n" + "\n".join(team_members))
        collaborators.extend(team_members)

    # maybe drop this into an OrgWrapper function
    # replacing the function label here in the loop
    for user in collaborators:
        if user not in collected_users:
            click.echo(f"Retrieving metrics for user: {user}")
            collected_users.append(user)
        else:
            click.echo(f"Skipping user (member of multiple teams): {user}")
        # collect metrics for the given user if not already covered by another team
        contributor_counts = metrics_calculators.contributor_actions(
            user=user, num_weeks=num_weeks
        )

        header = f"Contributions by week for [{user}]"
        click.echo(f"\n{'-' * len(header)}")
        click.echo(header)
        click.echo("-" * len(header))
        click.echo(tabulate(contributor_counts, tablefmt=table_format, headers="keys"))

        user_metrics_filename = METRICS_OUTPUT.joinpath(
            f"{Path(output_file_prefix).stem}-"
            f"{user}-"
            "contributor-"
            f"{datetime.now().isoformat(timespec='minutes')}.html"
        )
        click.echo(f"\nWriting contributor metrics as HTML to {user_metrics_filename}")
        file_io.write_to_output(
            user_metrics_filename,
            tabulate(contributor_counts, headers="keys", tablefmt="html"),
        )
