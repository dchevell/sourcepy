"""pagetitle uses a custom class to construct the desired object, and
allow for correct annotation of the function at the same time.
Note: this example relies on lxml, which is not part of the standard
library.
"""

import lxml.html

__all__ = ['pagetitle']

class HTML(lxml.html.HtmlElement):
    def __new__(cls, html_string, *args, **kwargs) -> lxml.html.HtmlElement:
        return lxml.html.fromstring(html_string)

def pagetitle(html: HTML) -> str:
    return html.find('.//title').text
