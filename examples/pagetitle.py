# pagetitle.py

import lxml.html # requires lxml to be installed

__all__ = ['pagetitle']

class HTML(lxml.html.HtmlElement):
    def __new__(cls, html_string, *args, **kwargs):
        return lxml.html.fromstring(html_string)

def pagetitle(html: HTML):
    return html.find('.//title').text
