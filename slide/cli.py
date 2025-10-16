import argparse
import os, sys

from slide.database.collectionPolicy import AgpCollectionPolicy, LogCollectionPolicy
from slide.feature.agpExtractionPolicy import Lithology, Summary
from slide.feature.featureExtractionEngine import FeatureEngine
from slide.feature.logExtractionPolicy import LogChannelsExtractionPolicy, LogExtractionPolicy
from slide.logger import Logger
from slide.downloaders import Aria2P
from slide.webscrapper import CatalogScrapper, AgpScrapper, WebScrapperEngine
from slide.database import AGPDownloadDAO, CatalogDownloadDAO, LogDownloadDAO
from slide.webscrapper import ConventionalLogScrapper

logging = Logger()
logger = logging.get_logger()


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    return False


def scrap_catalogs(data_path: str, download: bool, *args, **kwargs):
    scrapper = CatalogScrapper(out_dir=data_path)
    dao = CatalogDownloadDAO(f"{data_path}/download.db")
    downloader = Aria2P(cache_dao=dao) if download else None
    WebScrapperEngine(scrappers=scrapper, dao=dao, downloader=downloader).collect()


def scrap_agp(data_path: str, download: bool, *args, **kwargs):
    c_dao = CatalogDownloadDAO(f"{data_path}/download.db")
    scrapper = [AgpScrapper(c) for c in c_dao.fetch_all()]
    dao = AGPDownloadDAO(f"{data_path}/download.db")
    downloader = Aria2P(cache_dao=dao) if download else None
    WebScrapperEngine(scrappers=scrapper, dao=dao, downloader=downloader).collect()


def scrap_conventional_logs(data_path: str, download: bool, *args, **kwargs):
    c_dao = CatalogDownloadDAO(f"{data_path}/download.db")
    scrapper = [ConventionalLogScrapper(c) for c in c_dao.fetch_all()]
    dao = LogDownloadDAO(f"{data_path}/download.db")
    downloader = Aria2P(cache_dao=dao) if download else None
    WebScrapperEngine(scrappers=scrapper, dao=dao, downloader=downloader).collect()


def build_agp_lithology(data_path: str, *args, **kwargs):
    collection_policy = AgpCollectionPolicy(f"{data_path}/download.db")
    extraction_policy = Lithology()
    engine = FeatureEngine(policy=extraction_policy, data_collection_policy=collection_policy)
    engine.collect()


def build_agp_summary(data_path: str, *args, **kwargs):
    collection_policy = AgpCollectionPolicy(f"{data_path}/download.db")
    extraction_policy = Summary()
    engine = FeatureEngine(policy=extraction_policy, data_collection_policy=collection_policy)
    engine.collect()


def build_conventional_logs(data_path: str, *args, **kwargs):
    collection_policy = LogCollectionPolicy(f"{data_path}/download.db")
    extraction_policy = LogExtractionPolicy()
    engine = FeatureEngine(policy=extraction_policy, data_collection_policy=collection_policy)
    engine.collect()


def build_logs_channels(data_path: str, *args, **kwargs):
    collection_policy = LogCollectionPolicy(f"{data_path}/download.db")
    extraction_policy = LogChannelsExtractionPolicy()
    engine = FeatureEngine(policy=extraction_policy, data_collection_policy=collection_policy)
    engine.collect()


def make_shared_commands(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "-ll",
        "--log-level",
        type=str,
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        metavar="<LEVEL>",
        help="Set the logging level.\nChoices: [%(choices)s]\nDefault: %(default)s\n\n",
        default="INFO",
    )
    parser.add_argument(
        "-d",
        "--data-path",
        type=str,
        dest="data_path",
        metavar="<PATH>",
        help="Path to ANP basin composite and conventional profile files.\nDefault: %(default)s\n\n",
        default="./downloads",
    )
    return parser


def make_scrap_subparsers() -> dict:
    scrap_subparsers = {}
    scrap_subparsers["catalogs"] = {
        "help": "Scrap the catalogs from ANP basins database",
        "description": "Create a spider to peform webscrapping of catalogs at ANP basins database.",
        "func": scrap_catalogs,
    }
    scrap_subparsers["agp"] = {
        "help": "Scrap the AGP files from ANP basins database",
        "description": "Create a spider to peform webscrapping of AGP files at ANP basins database.",
        "func": scrap_agp,
    }
    scrap_subparsers["conventional-logs"] = {
        "help": "Scrap the conventional logs from ANP basins database",
        "description": "Create a spider to peform webscrapping of conventional logs at ANP basins database.",
        "func": scrap_conventional_logs,
    }
    return scrap_subparsers


def make_scrap_commands(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--download",
        type=str2bool,
        dest="download",
        metavar="<DOWNLOAD>",
        help="Enable downloading of files. (yes/no, true/false, 1/0)",
        default=True,
    )


def make_feature_subparsers() -> dict:
    feature_subparsers = {}
    feature_subparsers["agp-lithology"] = {
        "help": "Build the AGP lithology feature dataset from downloaded AGP files",
        "description": "Create a feature extraction engine to build the AGP lithology dataset from downloaded AGP files.",
        "func": build_agp_lithology,
    }
    feature_subparsers["agp-summary"] = {
        "help": "Build the AGP summary feature dataset from downloaded AGP files",
        "description": "Create a feature extraction engine to build the AGP summary dataset from downloaded AGP files.",
        "func": build_agp_summary,
    }
    feature_subparsers["conventional-logs"] = {
        "help": "Build the conventional logs feature dataset from downloaded conventional log files",
        "description": "Create a feature extraction engine to build the conventional logs dataset from downloaded conventional log files.",
        "func": build_conventional_logs,
    }
    feature_subparsers["logs-channels"] = {
        "help": "Build the logs channels feature dataset from downloaded conventional log files",
        "description": "Create a feature extraction engine to build the logs channels dataset from downloaded conventional log files.",
        "func": build_logs_channels,
    }
    return feature_subparsers


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SLIDE: A command line tool for Smart Line Identification and Data Extraction"
    )
    parser = make_shared_commands(parser)

    subparsers = parser.add_subparsers(dest="command", required=True, help="Main commands")

    # Scrap command
    parser_scrap = subparsers.add_parser(
        "scrap",
        help="Scrap the dataset from ANP basins database",
        description="Create a spider to peform webscrapping at ANP basins database.",
    )

    scrap_subparsers = parser_scrap.add_subparsers(dest="scrap_type", required=True, help="Scrap subcommands")

    for name, opts in make_scrap_subparsers().items():
        sub = scrap_subparsers.add_parser(name, help=opts["help"], description=opts["description"])
        sub.set_defaults(func=opts["func"])
        sub = make_scrap_commands(sub)

    parser_scrap = subparsers.add_parser(
        "feature",
        help="Build the feature dataset from downloaded files",
        description="Create a feature extraction engine to build the dataset from downloaded files.",
    )

    scrap_subparsers = parser_scrap.add_subparsers(dest="feature_type", required=True, help="Feature subcommands")

    for name, opts in make_feature_subparsers().items():
        sub = scrap_subparsers.add_parser(name, help=opts["help"], description=opts["description"])
        sub.set_defaults(func=opts["func"])

    return parser


def cli() -> None:
    """Main entry point for the slide command line interface."""
    parser = build_argparser()
    parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter
    args = parser.parse_args()
    args_dict = vars(args).copy()
    logging.set_level(args_dict.pop("log_level"))

    try:
        args.func(**args_dict)
    except Exception:
        raise
    os._exit(0)


if __name__ == "__main__":
    sys.argv = ["script.py", "-ll", "DEBUG", "scrap", "-s", "0"]
    cli()
