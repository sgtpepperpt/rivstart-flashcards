from dataclasses import dataclass
from pathlib import Path
from time import sleep
from common import extract_text, simple_font

from deep_translator import GoogleTranslator
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams
from pdfminer.layout import LTChar, LTAnno


@dataclass
class Pair:
    chapter: str
    text: str
    swedish: str
    english: str


@dataclass
class _Element:
    text: str
    font: str
    size: float

    def __repr__(self):
        return f'{self.text} [{self.font}]'


@dataclass
class _Marker:
    type: int
    val: str

    def __repr__(self):
        return f'MARKER CHAPTER {self.val}' if type == 0 else f'MARKER TEXT "{self.val}"'


def _proccess_pdf(file):
    path = Path(file).expanduser()
    pages = extract_pages(path, laparams=LAParams(line_margin=0.5))
    lines = extract_text(pages)

    elements = []

    for line in lines:
        elems = []

        for obj in line:
            # only expect LTChar or LTAnno
            if not isinstance(obj, LTChar | LTAnno):
                raise Exception()

            if isinstance(obj, LTAnno):
                continue

            # extract first element
            if len(elems) == 0:
                # we always expect a normal char element
                if not isinstance(obj, LTChar):
                    raise Exception()

                elems.append(_Element(obj.get_text(), simple_font(obj.fontname), obj.size))
                continue

            # join separate chars together
            prev_elem = elems[-1]
            if isinstance(prev_elem, _Element) and simple_font(obj.fontname) == prev_elem.font and obj.size == prev_elem.size:
                prev_elem.text += obj.get_text()
            else:
                elems.append(_Element(obj.get_text(), simple_font(obj.fontname), obj.size))

        elements.append(elems)

    return elements


def _detect_marker_elements(elements):
    new_elements = []

    for elem in [elem[0] for elem in elements]:
        if round(elem.size) == 18.0:
            if elem.text.isnumeric():
                new_elements.append(_Marker(0, elem.text))
                continue
            else:
                new_elements.append(_Marker(1, elem.text))
                continue

        # ignore page numbers
        if elem.font == 'AGaramondPro-Regular':
            continue

        if elem.font == 'MyriadPro-Regular' and round(elem.size) == 16:
            new_elements.append(elem)
            continue

        raise Exception()

    return new_elements


def _clean(elements):
    new_elements = []

    for i, elem in enumerate(elements):
        # for B1B2
        if isinstance(elem, _Element) and elem.text == 'en aktie':
            new_elements.append(_Marker(0, '2'))

        if isinstance(elem, _Element) and elem.text == 'allergisk':
            new_elements.append(_Marker(0, '4'))

        if isinstance(elem, _Element) and elem.text == 'beredd' and not (isinstance(elements[i-1], _Element) and elements[i-1].text == 'behåller'):
            new_elements.append(_Marker(0, '7'))

        if isinstance(elem, _Element) and elem.text == 'alldeles':
            new_elements.append(_Marker(0, '9'))

        if isinstance(elem, _Element) and elem.text.strip() == 'anställningsintervju':
            new_elements[-1].text = new_elements[-1].text[:-1] + elem.text
            continue

        if isinstance(elem, _Element) and elem.text.strip() == 'arbetslivserfarenhet':
            new_elements[-1].text += elem.text
            continue

        # for B2C1
        if isinstance(elem, _Element) and elem.text.strip() == 'nämnare':
            new_elements[-1].text += elem.text
            continue

        if isinstance(elem, _Marker) and elem.type == 0:
            val = int(elem.val)
            if val == 44:
                elem.val = '4'
            elif val == 45:
                elem.val = '5'
            elif val == 46:
                elem.val = '6'
            elif str(val).startswith('144'):
                elem.val = str(val)[3:]

            elif val > 18:
                raise Exception()

        new_elements.append(elem)

    return new_elements


def _create_pairs(elements, translate):
    pairs = []

    for line in [(i, e) for i, e in enumerate(elements)]:
        if not isinstance(line[1], _Element):
            continue

        swedish = line[1].text
        english = ''

        if translate:
            tries = 0
            while True:
                try:
                    english = GoogleTranslator(source='sv', target='en').translate(swedish)
                    sleep(2)
                    break
                except Exception as e:
                    if tries > 5:
                        raise e

                    tries += 1
                    sleep(10)

        chapter = [e for e in elements[:line[0]] if isinstance(e, _Marker) and e.type == 0][-1]
        text = [e for e in elements[:line[0]] if isinstance(e, _Marker) and e.type == 1]
        text = None if len(text) == 0 else str(text[-1].val)

        pairs.append(Pair(chapter.val, text, swedish, english))

    return pairs


def get_pairs(file, translate=True):
    elements = _proccess_pdf(file)
    elements = _detect_marker_elements(elements)
    elements = _clean(elements)

    return _create_pairs(elements, translate)
