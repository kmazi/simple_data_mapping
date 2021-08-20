"""Define helper functions for fetching and processing data from api."""

import json
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional

from aiohttp import ClientSession as Session
from pydantic import HttpUrl
from requests.exceptions import HTTPError


def logger(name:str):
    logging.basicConfig(level="INFO")
    logger = logging.getLogger(name)
    return logger

log = logger(__name__)

async def fetch(session:Session, url: HttpUrl) -> Optional[List[Dict]]:
    """Fetch all data in api via given url.
    Arguments:
    ---
     url - Url to access api

    Returns:
    ---
     A dictionary containing response from the server or None if there was an error
    """
    response = None
    try:
        response = await session.get(url)
        response.raise_for_status()
    except HTTPError as http_er:
        log.error("An http error occurred:", exc_info=True)
        response = None
    except Exception as e:
        log.error("A general exception ocurred: %s", str(e), exc_info=True)
        response = None
    else:
        response = await response.json()
    return response

def pretty_print(data:Dict) -> str:
    """.pretty print data object in json format"""
    mod: datetime = data.get("modification_date")
    pub: datetime = data.get("publication_date")
    if mod:
        data["modification_date"] = mod.isoformat()
    if pub:
        data["publication_date"] = pub.isoformat()
    data = json.dumps(data, indent=2)
    return data


def to_datetime(datetime_str: str, sep: str = ":") -> datetime:
    """Convert datetime formatted string to datetime object.
    Arguments:
    ---
     datetime_str: datetime value in string
     sep: separator for time in datetime string

    returns:
    ---
     return datetime object representing the input string
    """
    return datetime.strptime(datetime_str, f"%Y-%m-%d-%H{sep}%M{sep}%S")
