import json
import time
from pathlib import Path

import click
from tabulate import tabulate

from config import settings
from utils import github_client


# parent click group for gather and graph commands
@click.group()
def generate_metrics():
    pass


@generate_metrics.command("gather", help="Gather PR metrics for given GH repo")
@click.option("--repo-name", default="SatelliteQE/robottelo")
@click.option(
    "--metric", type=click.Choice(["time_to_comment"]), default="time_to_comment"
)
@click.option(
    "--file-output",
    default=settings.get("metrics_output_file_prefix", "gh-pr-metrics"),
    help="Will only take file name (with or without extension), but not a full path."
    "Will append an epoch timestamp to the file name.",
)
def gather(repo_name, metric, output):
    metrics = getattr(github_client, metric)(
        repo_name=repo_name
    )  # execute method from github util

    click.echo(tabulate(metrics.values(), showindex=metrics.keys(), headers="keys"))

    output_filename = f"{Path(output.stem)}-{int(time())}.json"
    with open(output_filename, "w") as output_file:
        json.dump(metrics, output_file)
