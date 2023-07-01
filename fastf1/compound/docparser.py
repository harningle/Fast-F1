from io import BytesIO
import re
from tqdm.auto import tqdm

from pypdf import PdfReader
import requests


def get_event_note(year: int, race: str, **kwargs) -> list:
    """Find the event note doc. for a given GP

    :param year: int: Year
    :param race: str: GP name, e.g. British
    :param kwargs: Optional arguments for the requests.get() function
    :return: list: List of URLs for all potential race directors' event note PDF
    """

    # Hard code the FIA docs. URL for seasons since 2019
    match year:
        case 2019:
            year = '2019-971'
        case 2020:
            year = '2020-1059'
        case 2021:
            year = '2021-1108'
        case 2022:
            year = '2022-2005'
        case 2023:
            year = '2023-2042'
        case _:
            raise ValueError(f'Year {year} not supported')
    url = f'https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/' \
          f'season/season-{year}/event/{race.title()} Grand Prix'
    resp = requests.get(url, **kwargs)

    # Find docs. with "event notes" or "Pirelli" in the title
    docs = re.findall(r'href="(.+?).pdf"', resp.text)
    docs = [doc for doc in docs if 'event notes' in doc.lower() or 'pirelli' in doc.lower()]
    return docs


def get_pdf(url: str, **kwargs) -> bytes:
    """Download a PDF file from the given URL.

    :param url: URL of the PDF FIA document
    :param kwargs: Optional arguments for `requests.get()`
    :return: PDF file content
    """

    # Get the PDF file from the URL
    resp = requests.get(url, **kwargs)

    # Try three times if the above request fails
    cnt = 0
    while not resp.ok and cnt < 3:
        resp = requests.get(url, **kwargs)
        cnt += 1
    return resp.content


def parse_compound(pdf: bytes) -> set[str] | None:
    """Parse the PDF file and see if we can find the tyre compound in it

    :param pdf: PDF file content
    :return: compound information or None if not found
    """

    # Go through the pages and look for tyre compound
    pdf = BytesIO(pdf)
    reader = PdfReader(pdf)
    for page in reader.pages:
        text = page.extract_text()
        if 'Compounds selection' in text:
            compound = set(re.findall(r'(C\d)', text))
            return compound


def get_event_compound(year: int, race: str, **kwargs) -> set[str]:
    """Parse the PDF file and see if we can find the tyre compound in it

    :param year: Year
    :param race: GP name, e.g. British
    :param kwargs: Optional arguments for the requests.get() function
    :return: Compound
    """

    # Go to the FIA website and find all PDF links
    docs = get_event_note(year, race, **kwargs)

    # Find compound in each PDF file
    for doc in tqdm(docs, desc=f'searching for tyre compounds in {race} in {year}'):
        url = f'https://www.fia.com{doc}.pdf'
        pdf = get_pdf(url, **kwargs)
        compound = parse_compound(pdf)
        if compound:
            return compound
