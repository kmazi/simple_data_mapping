"""This is the module that runs the entire app(fetches data from api and displays it) like an entry point."""

import argparse
import asyncio
import logging
import time
from string import Template

import aiohttp
import requests
from aiohttp import ClientSession

from models import Article

LIST_OF_ARTICLES_URL = "https://mapping-test.fra1.digitaloceanspaces.com/data/list.json"


async def execute(delay: int):
    """Pull data from apis, map using classes in models.py and print value.
    Arguments:
    ---
     delay - Specifies how long before app pulls an update to data from api
    """

    # persist session object across requests
    async with ClientSession() as session:
        with requests.Session() as sync_session:
            while True:
                headings = sync_session.get(LIST_OF_ARTICLES_URL).json()
                if headings is None:
                    logging.error(
                        "Script could not fetch articles from server owing to errors.",
                        exc_info=True,
                    )
                else:
                    # fetch article details in coroutine
                    await asyncio.gather(
                        *[Article.details(session, heading) for heading in headings]
                    )
                # run logic after 5 mins or any time set
                time.sleep(delay)


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-d",
        "--delay",
        nargs="?",
        default=300,
        help="How long in seconds app should delay before fetching an update",
    )

    args: argparse.Namespace = parser.parse_args()
    delay = int(args.delay)
    asyncio.run(execute(delay))
