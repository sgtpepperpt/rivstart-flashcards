import re
from typing import Any, Iterable

from pdfminer.layout import LTTextLineHorizontal


def extract_text(pages):
    lines = []

    def show_ltitem_hierarchy(o: Any):
        if isinstance(o, LTTextLineHorizontal):
            lines.append(o)

        if isinstance(o, Iterable):
            for i in o:
                show_ltitem_hierarchy(i)

    show_ltitem_hierarchy(pages)
    return lines


def simple_font(font):
    match = re.match(r'.*\+(.*)', font)
    return match.group(1) if match else font
