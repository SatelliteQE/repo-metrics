# import json
# from collections import OrderedDict
from pathlib import Path
from time import time

import click
from tabulate import tabulate

from config import settings
from utils import file_io
from utils import metrics_calculators


# keys that will be read from settings files (dynaconf parsing) for command input defaults
SETTINGS_OUTPUT_PREFIX = "metrics_output_file_prefix"
SETTINGS_REVIEWER_TEAMS = "reviewer_teams"


# parent click group for gather and graph commands
@click.group()
def gather():
    pass


# reused options for multiple metrics functions
output_prefix_option = click.option(
    "--file-output-prefix",
    default=settings.get(SETTINGS_OUTPUT_PREFIX, "gathered-metrics"),
    help="Will only take file name (with or without extension), but not a full path."
    "Will append the metric name an epoch timestamp to the file name.",
)
org_name_option = click.option(
    "--org-name",
    default="SatelliteQE",
    help="The organization or user, for review counts across multiple repos",
)
repo_name_option = click.option(
    "--repo-name", default="robottelo", help="The repository name, like robottelo",
)
pr_count_option = click.option(
    "--pr-count",
    default=50,
    help="Number of PRs to include in metrics counts, will start from most recently created",
)


@gather.command(
    "single_pr_metrics",
    help="Gather metrics about individual PRs for a GH repo (SatelliteQE/robottelo)",
)
@org_name_option
@repo_name_option
@output_prefix_option
@pr_count_option
def time_to_review(repo_name, org_name, file_output_prefix, pr_count):
    gathered_metrics = metrics_calculators.single_pr_metrics(
        organization=org_name, repo_name=repo_name, pr_count=pr_count
    )

    click.echo("Gathered metrics for time to review", color="cyan")
    click.echo("-----------------------------------", color="cyan")
    click.echo(
        tabulate(gathered_metrics, headers="keys", tablefmt="github", floatfmt=".1f",)
    )

    output_filename = f"{Path(file_output_prefix).stem}-{__name__}-{int(time())}.json"
    click.echo(f"Writing metrics as JSON to {output_filename}")
    file_io.write_to_output(output_filename, gathered_metrics)


@gather.command("reviewer_actions")
@org_name_option
@output_prefix_option
def reviewer_actions(org_name, file_output_prefix):
    """ Generate metrics for tier reviewer groups, and general contributors

    Will collect tier reviewer teams from the github org
    Tier reviewer teams will read from settings file, and default to what SatelliteQE uses

    """
    team_slugs = settings.get(
        "reviewers_teams", ["tier-1-reviewers", "tier-2-reviewers"]
    )
    reviewer_metrics = metrics_calculators.reviewer_actions(org_name, team_slugs)

    # TODO: header per team slugs, read from reviewer_metrics dict
    click.echo("Gathered metrics for reviewer actions [TIER 1]", color="cyan")
    click.echo("----------------------------------------------", color="cyan")
    click.echo(
        tabulate(
            reviewer_metrics.values(),
            showindex=reviewer_metrics.keys(),
            headers="keys",
            tablefmt="github",
            floatfmt=".2f",
        )
    )


# for debugging purposes
if __name__ == "__main__":
    metrics = gather()
