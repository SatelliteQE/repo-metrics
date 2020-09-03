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
SETTINGS_OUTPUT_PREFIX = "pr_metrics_output_file_prefix"
SETTINGS_REVIEWER_TEAMS = "reviewer_teams"


# parent click group for gather and graph commands
@click.group()
def gather():
    pass


# reused options for multiple metrics functions
output_prefix_option = click.option(
    "--file-output-prefix",
    default=settings.get(SETTINGS_OUTPUT_PREFIX, "pr-metrics"),
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
def time_to_review(org, repo, file_output_prefix, pr_count):
    for repo_name in repo:
        pr_metrics, stat_metrics = metrics_calculators.single_pr_metrics(
            organization=org, repository=repo_name, pr_count=pr_count
        )

        click.echo("-----------------------------------")
        click.echo(f"Review Metrics By PR for [{repo_name}]")
        click.echo("-----------------------------------")
        click.echo(
            tabulate(pr_metrics, headers="keys", tablefmt="github", floatfmt=".1f")
        )

        click.echo("-----------------------------------")
        click.echo(f"Review Metric Statistics for [{repo_name}]")
        click.echo("-----------------------------------")
        click.echo(
            tabulate(stat_metrics, headers="keys", tablefmt="github", floatfmt=".1f")
        )

        pr_metrics_filename = (
            f"{Path(file_output_prefix).stem}-"
            f"{org}-"
            f"{repo_name}-"
            "pr_metrics-"
            f"{int(time())}.html"
        )
        click.echo(f"Writing PR metrics as HTML to {pr_metrics_filename}")
        file_io.write_to_output(
            pr_metrics_filename,
            tabulate(pr_metrics, headers="keys", tablefmt="html", floatfmt=".1f"),
        )

        stat_metrics_filename = (
            f"{Path(file_output_prefix).stem}-"
            f"{org}-"
            f"{repo_name}-"
            "stat_metrics-"
            f"{int(time())}.html"
        )
        click.echo(f"Writing statistics metrics as HTML to {stat_metrics_filename}")
        file_io.write_to_output(
            stat_metrics_filename,
            tabulate(stat_metrics, headers="keys", tablefmt="html", floatfmt=".1f"),
        )


@gather.command("reviewer_actions")
@org_name_option
@repo_name_option
@output_prefix_option
@pr_count_option
def reviewer_actions(org, repo, file_output_prefix, pr_count):
    """ Generate metrics for tier reviewer groups, and general contributors

    Will collect tier reviewer teams from the github org
    Tier reviewer teams will read from settings file, and default to what SatelliteQE uses

    """
    for repo_name in repo:
        t1_metrics, t2_metrics = metrics_calculators.reviewer_actions(
            organization=org, repository=repo_name, pr_count=pr_count
        )
        header = f"Tier1 Reviewer actions by week for [{repo_name}]"
        click.echo("-" * len(header))
        click.echo(header)
        click.echo("-" * len(header))
        click.echo(tabulate(t1_metrics, headers="keys", tablefmt="github"))

        header = f"Tier2 Reviewer actions by week for [{repo_name}]"
        click.echo("-" * len(header))
        click.echo(header)
        click.echo("-" * len(header))
        click.echo(tabulate(t2_metrics, headers="keys", tablefmt="github"))

        tier1_metrics_filename = (
            f"{Path(file_output_prefix).stem}-"
            f"{org}-"
            f"{repo_name}-"
            "tier1_reviewers-"
            f"{int(time())}.html"
        )
        click.echo(f"Writing PR metrics as HTML to {tier1_metrics_filename}")
        file_io.write_to_output(
            tier1_metrics_filename,
            tabulate(t1_metrics, headers="keys", tablefmt="html"),
        )

        tier2_metrics_filename = (
            f"{Path(file_output_prefix).stem}-"
            f"{org}-"
            f"{repo_name}-"
            "tier2_reviewers-"
            f"{int(time())}.html"
        )
        click.echo(f"Writing PR metrics as HTML to {tier2_metrics_filename}")
        file_io.write_to_output(
            tier2_metrics_filename,
            tabulate(t2_metrics, headers="keys", tablefmt="html"),
        )


# for debugging purposes
if __name__ == "__main__":
    metrics = gather()
