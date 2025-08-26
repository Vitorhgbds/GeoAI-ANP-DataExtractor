import argparse
import os, sys

from slide.pipelines.new_scrapping_pipeline import NewScrappingPipeline
from slide.pipelines.scraping import ANPScrapingPipeline
from slide.logger import Logger

logging = Logger()
logger = logging.get_logger()

def scrap(data_path: str, *args, **kwargs):
    pipeline = NewScrappingPipeline() 
    #ANPScrapingPipeline(download_directory=data_path, **kwargs)
    pipeline.run()

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
        default="./data",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        dest="config_path",
        metavar="<PATH>",
        help="Path to config file.\nDefault: %(default)s\n\n",
        default=None,
    )
    return parser

def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SLIDE: A command line tool for Smart Line Identification and Data Extraction",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser = make_shared_commands(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    parent_parser = argparse.ArgumentParser(add_help=False)

    parser_scrap = subparsers.add_parser(
        "scrap",
        help="Scrap the latest ANP basin composite and conventional profiles.",
        description="Create a spider to peform webscrapping at ANP basins database.",
        parents=[parent_parser],
    )
    parser_scrap.add_argument(
        "-s",
        "--seconds-delay",
        type=float,
        dest="seconds_delay",
        metavar="<SECONDS>",
        help="Ban prevention delay in seconds\nDefault: %(default)s\n\n",
        default=0.0,
    )
    return parser

def cli() -> None:
    """Main entry point for the slide command line interface."""
    parser = build_argparser()

    args = parser.parse_args()
    args_dict = vars(args).copy()
    logging.set_level(args_dict.pop("log_level"))

    try:
        match args.command:
            case "scrap":
                scrap(**args_dict)
            case _:
                parser.print_help()
    except Exception as e:
        raise
    os._exit(0)


if __name__ == "__main__":
    sys.argv = ["script.py", "-ll", "DEBUG", "scrap", "-s", "0"]
    cli()