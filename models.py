from datetime import datetime
from string import Template
from typing import Dict, List, Literal, Optional, Set, Union

from pydantic import BaseModel, Field, HttpUrl
from requests import Session

from util import fetch, logger, pretty_print, to_datetime

log = logger(__name__)

ARTICLE_DETAIL_URL = Template(
    "https://mapping-test.fra1.digitaloceanspaces.com/data/articles/${article_id}.json"
)
BASE_MEDIA_URL = Template(
    "https://mapping-test.fra1.digitaloceanspaces.com/data/media/${article_id}.json"
)


class Section(BaseModel):
    def __repr__(self):
        return pretty_print(self.dict())


class HeaderSection(Section):
    type: Literal["header"] = Field(
        ..., description="Section type - 'header'", example="header"
    )
    level: int = Field(
        ...,
        description="The level of the header. The higher the number, the less important.",
        example="1",
    )
    text: str = Field(
        ...,
        description="Content of the header.",
        example="This is how you define a header",
    )


class TitleSection(Section):
    type: Literal["title"] = Field(
        ..., description="Section type - 'title'", example="title"
    )
    text: str = Field(
        ...,
        description="Content of the title.",
        example="This is how you define a title.",
    )


class LeadSection(Section):
    type: Literal["lead"] = Field(
        ..., description="Section type - 'lead'", example="lead"
    )
    text: str = Field(
        ...,
        description="Content of the lead.",
        example="This is how you define a lead.",
    )


class TextSection(Section):
    type: Literal["text"] = Field(
        ..., description="Section type - 'text'", example="text"
    )
    text: str = Field(
        ...,
        description="Content of the text.",
        example="This is how you define a text.",
    )


class ImageSection(Section):
    type: Literal["image"] = Field(
        ..., description="Section type - 'image'", example="image"
    )
    url: HttpUrl = Field(
        ..., description="Url to the image", example="https://url.to.image/image.jpg"
    )
    alt: Optional[str] = Field(
        None,
        description="Alternative text to display if image does not appear.",
        example="The alternative text.",
    )
    caption: Optional[str] = Field(
        None,
        description="The description of the image.",
        example="The description of the image.",
    )
    source: Optional[str] = Field(
        None,
        description="An Author or Organization Name",
        example="Pawel Glimos",
    )


class MediaSection(Section):
    type: Literal["media"] = Field(
        ..., description="Section type - 'media'", example="media"
    )
    id: str = Field(
        ...,
        description="Provider internal id of the media",
        example="media_id",
    )
    url: HttpUrl = Field(
        ..., description="Url to the media", example="https://some.website/media.mp4"
    )
    thumbnail: Optional[HttpUrl] = Field(
        None,
        description="Url to the thumbnail of the media",
        example="https://some.website/article/thumb.jpg",
    )
    caption: Optional[str] = Field(
        None, description="Caption of the media", example="This video shows a tutorial"
    )
    author: Optional[str] = Field(
        None, description="Name of the author of the media", example="Some Author"
    )
    publication_date: datetime = Field(
        ..., description="Datetime of media publication", example="2020-07-08T20:50:43Z"
    )
    modification_date: Optional[datetime] = Field(
        None,
        description="Datetime of media modification",
        example="2020-07-08T20:50:43Z",
    )
    duration: Optional[int] = Field(
        None, description="Duration of the media in seconds", example=120
    )


SECTION_TYPES = Union[
    TextSection, TitleSection, LeadSection, HeaderSection, ImageSection, MediaSection
]


class Article(BaseModel):
    id: str = Field(..., description="Internal provider id", example="article_id")
    original_language: str = Field(
        ..., description="Article original language", example="en"
    )
    url: HttpUrl = Field(
        ...,
        description="Url to the article",
        example="https://some.website/article.html",
    )
    thumbnail: Optional[HttpUrl] = Field(
        None,
        description="Url to the thumbnail of the article",
        example="https://some.website/article/thumb.jpg",
    )
    categories: Optional[Set[str]] = Field(
        None, description="List of article categories", example=["news", "local"]
    )
    tags: Optional[Set[str]] = Field(
        None, description="List of article tags", example=["news", "local"]
    )
    author: Optional[str] = Field(
        None, description="Name of the author of the article", example="Some Author"
    )
    publication_date: datetime = Field(
        ...,
        description="Datetime of article publication",
        example="2020-07-08T20:50:43Z",
    )
    modification_date: Optional[datetime] = Field(
        description="Datetime of article modification", default_factory=datetime.now
    )
    sections: List[Union[SECTION_TYPES]]

    @staticmethod
    async def _extract_details(session: Session, response: Dict) -> Dict:
        """Fetch details of article represented by article_info.
        Arguments:
        ---
        article_info: Dictionary containing id and title of article
        """
        # Create article object and get values from api response
        detail = {}
        detail["id"] = response["id"]
        detail["original_language"] = response["original_language"]
        detail["url"] = ARTICLE_DETAIL_URL.substitute(article_id=detail["id"])
        detail["thumbnail"] = response.get("thumbnail")
        # create category set if val is available else set to None
        cat = response.get("category")
        detail["categories"] = set(cat) if cat else cat
        # create tag set if val is available else set to None
        tag = response.get("tag")
        detail["tags"] = set(tag) if tag else tag

        detail["author"] = response.get("author")
        detail["publication_date"] = response["pub_date"]
        detail["publication_date"] = to_datetime(detail["publication_date"], sep=";")
        mod_date = response.get("mod_date", datetime.now().isoformat())
        detail["modification_date"] = to_datetime(mod_date)
        # Extract sections
        sections = response.get("sections")
        detail["sections"] = await Article._extract_sections(
            session, section_headers=sections, article_id=detail["id"]
        )

        return detail

    @staticmethod
    async def details(session: Session, heading: Dict):
        """Fetch details of an article."
        Arguments:
        ---
         session - request session to fetch used for connection
         heading - dictionary containing id and title of article
        """
        url = ARTICLE_DETAIL_URL.substitute(article_id=heading["id"])
        response = await fetch(session, url)
        if response is None:
            log.info("Error fetching detail for article with id: %s", heading["id"])
            return
        # extract details from response
        detail = await Article._extract_details(session, response)
        article = Article(**detail)
        log.info("\n----------------- logging Article with id=%s", article.id)
        print(article)
        log.info("\n-----------------")

    @staticmethod
    def _map_section(stype: str) -> Dict:
        """Get exact section type from string in response."""
        mapper = {
            "text": {"section_type": TextSection, "fields": ["type", "text"]},
            "media": {
                "section_type": MediaSection,
                "fields": [
                    "type",
                    "id",
                    "url",
                    "thumbnail",
                    "caption",
                    "author",
                    "publication_date",
                    "modification_date",
                    "duration",
                ],
            },
            "image": {
                "section_type": ImageSection,
                "fields": ["type", "url", "alt", "caption", "source"],
            },
            "lead": {"section_type": LeadSection, "fields": ["type", "text"]},
            "title": {"section_type": TitleSection, "fields": ["type", "text"]},
            "header": {"section_type": HeaderSection, "fields": ["type", "level", "text"]},
        }
        return mapper.get(stype)

    @staticmethod
    async def _fetch_media_details(
        session: Session, article_id: str
    ) -> Dict[str, Dict]:
        """fetch media data once for media and image type."""
        image_media_data = {}
        url = BASE_MEDIA_URL.substitute(article_id=article_id)
        media_data = await fetch(session, url)
        if media_data is None:
            log.info(
                "Error occurred while fetching section for article id: %s",
                article_id,
            )
            return None
        for media in media_data:
            image_media_data[media["id"]] = media
        return image_media_data

    @staticmethod
    async def _extract_sections(
        session: Session, section_headers: List[Dict], article_id: str
    ) -> List[SECTION_TYPES]:
        """Get sections from article data."""
        sections = []
        image_media_data = {}
        for header in section_headers:
            s_type = header["type"]
            # map section type using dictionary from _map_section method
            s_type = Article._map_section(s_type)
            SectionType = s_type["section_type"]
            # read values from field and map them to section attributes
            section_data = {}
            if SectionType in [MediaSection, ImageSection]:
                if image_media_data == {}:
                    image_media_data = await Article._fetch_media_details(
                                            session, article_id=article_id
                                        )
                # skip to the next section if fetching a media section fails
                if image_media_data is None:
                    continue
                val = image_media_data[header.get("id")]
                header.update(val)
                # update section type especially for image type
                s_type = Article._map_section(header["type"])
                SectionType = s_type["section_type"]
            # loop through section type fields and supply values
            for field in s_type["fields"]:
                if field == "publication_date":
                    section_data["publication_date"] = to_datetime(header["pub_date"], sep=";")
                else:
                    section_data[field] = header.get(field)
            section = SectionType(**section_data)
            sections.append(section)
        return sections

    def __repr__(self):
        """Define string representative of article object."""
        return pretty_print(self.dict())
