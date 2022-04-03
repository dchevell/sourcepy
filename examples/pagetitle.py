"""pagetitle uses a custom class to construct the desired object, and
allow for correct annotation of the function at the same time.
Note: this example relies on lxml, which is not part of the standard
library.
"""

from lxml.html import HtmlElement
from lxml.html import fromstring as htmlfromstring

__all__ = ['pagetitle']

class HTML(HtmlElement):
    def __new__(cls, html_string, *args, **kwargs) -> HtmlElement:
        return htmlfromstring(html_string)

def pagetitle(html: HTML) -> str:
    return html.find('.//title').text
