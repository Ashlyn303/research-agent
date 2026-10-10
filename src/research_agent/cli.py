"""Command-line entry point: `research-agent "your question"`."""

import argparse
import logging
import sys
import time

from dotenv import find_dotenv, load_dotenv

from research_agent.agent import RefusalError, build_agent, final_answer
from research_agent.config import ConfigError, load_settings
from research_agent.run_info import run_config
from research_agent.usage import summarize_usage

DEFAULT_QUESTION = "What are recent approaches to de novo protein design?"

logger = logging.getLogger("research_agent")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="research-agent",
        description="Search PubMed and answer a research question with cited papers.",
    )
    parser.add_argument("question", nargs="*", help="research question to answer")
    parser.add_argument("-v", "--verbose", action="store_true", help="log each tool call")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Read .env from the current folder. LangSmith reads its settings from the environment.
    load_dotenv(find_dotenv(usecwd=True))
    try:
        settings = load_settings()
    except ConfigError as e:
        logger.error("%s", e)
        return 2

    question = " ".join(args.question) or DEFAULT_QUESTION
    agent = build_agent(settings)
    started = time.monotonic()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]}, config=run_config(settings, "cli")
    )
    usage = summarize_usage(result["messages"], seconds=time.monotonic() - started)
    logger.info("Run used %s", usage.summary())
    try:
        print(final_answer(result))
    except RefusalError as e:
        logger.error("%s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
