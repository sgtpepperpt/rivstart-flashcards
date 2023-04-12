import re
from dataclasses import dataclass
from pathlib import Path
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextLineHorizontal, LTChar, LTAnno
from typing import Any, Iterable, List, Tuple


@dataclass
class Pair:
    chapter: str
    page: str
    swedish: str
    swedish_conjugation: str
    english: str


@dataclass
class _Element:
    text: str
    font: str
    size: float

    def __repr__(self):
        return f'{self.text} [{self.font}]'


@dataclass
class _Separator:
    type: int

    def __repr__(self):
        if self.type == 0:
            return 'ANNO NL'
        elif self.type == 1:
            return 'ANNO SP'
        elif self.type == 2:
            return 'EMPTY'


@dataclass
class _Marker:
    type: int
    val: int

    def __repr__(self):
        if self.type == 0:
            return f'MARKER CHAPTER {self.val}'
        elif self.type == 1:
            return f'MARKER PAGE {self.val}'
        elif self.type == 2:
            return 'MARKER CLASS'


def _extract_text(pages):
    lines = []

    def show_ltitem_hierarchy(o: Any):
        if isinstance(o, LTTextLineHorizontal):
            lines.append(o)

        if isinstance(o, Iterable):
            for i in o:
                show_ltitem_hierarchy(i)

    show_ltitem_hierarchy(pages)
    return lines


def _simple_font(font):
    match = re.match(r'.*\+(.*)', font)
    return match.group(1) if match else font


def _proccess_pdf(file):
    path = Path(file).expanduser()
    pages = extract_pages(path)
    lines = _extract_text(pages)

    elements = []

    for line in lines:
        elems = []

        for obj in line:
            # only expect LTChar or LTAnno
            if not isinstance(obj, LTChar | LTAnno):
                raise Exception()

            # extract first element
            if len(elems) == 0:
                # we always expect a normal char element
                if not isinstance(obj, LTChar):
                    raise Exception()

                elems.append(_Element(obj.get_text(), _simple_font(obj.fontname), obj.size))
                continue

            # LTAnno objs should always be separators
            if isinstance(obj, LTAnno):
                if obj.get_text() == ' ':
                    elems.append(_Separator(1))
                elif obj.get_text() == '\n':
                    elems.append(_Separator(0))
                else:
                    raise Exception()
                continue

            # if char is only blank space treat as separator
            if len(obj.get_text().strip()) == 0:
                elems.append(_Separator(2))
                continue

            # join separate chars together
            prev_elem = elems[-1]
            if isinstance(prev_elem, _Element) and _simple_font(
                    obj.fontname) == prev_elem.font and obj.size == prev_elem.size:
                prev_elem.text += obj.get_text()
            else:
                elems.append(_Element(obj.get_text(), _simple_font(obj.fontname), obj.size))

        elements.append(elems)
    return elements


def _detect_marker_elems(elements):
    new_elements = []

    for line in elements:
        first_elem = line[0]

        if first_elem.text.startswith('Klassrumsfraser'):
            new_elements.append(_Marker(2, -1))

        elif first_elem.text.startswith('Kapitel'):
            number = int([e for e in line if isinstance(e, _Element) and e.text.isnumeric()][0].text)
            new_elements.append(_Marker(0, number))

        elif first_elem.text.startswith('Sidan'):
            # cover case where page number has no space
            match = re.match(r'Sidan([0-9]+)', first_elem.text)
            if match:
                number = int(match.group(1))
            else:
                number = int([e for e in line if isinstance(e, _Element) and e.text.isnumeric()][0].text)
            new_elements.append(_Marker(1, number))

        elif first_elem.text.startswith(('A1+A2', 'B1+B2')):
            # ignore
            continue

        else:
            new_elements.append(line)

    return new_elements


def _join_similar(line, has_anno_spacing, space=True):
    new_line = []
    parts = 0
    prev = None

    last_space = [s for i, s in enumerate(line) if isinstance(s, _Separator) and len(line) > i + 1][-1]

    for e in line:
        if not isinstance(e, _Element):
            new_line.append(e)
            continue

        if prev and e.font == prev.font and e.size == prev.size:
            # if consecutive elements have the same font and size join them
            prev.text += (' ' if space else '') + e.text
        else:
            prev = e
            new_line.append(e)
            parts += 1

    if not has_anno_spacing:
        # if the last space was put at the end move it back to separate
        pos = [i for i, e in enumerate(new_line) if e is last_space][0]
        elems = [e for e in new_line if isinstance(e, _Element)]

        if len(elems) > 1 and pos + 1 == len(new_line) and elems[-2].font != elems[-1].font:
            last_elem_i = [i for i, e in enumerate(new_line) if e == elems[-1]][0]
            new_line.insert(last_elem_i, last_space)

    return _remove_end_empty(new_line)


def _remove_end_empty(line):
    while isinstance(line[-1], _Separator) and line[-1].type in [0, 2]:
        line = line[:-1]
    return line


def _cleanup_lines(elements):
    store = None

    new_elements = []
    for line in elements:
        # ignore already processed lines
        if not isinstance(line, List):
            new_elements.append(line)
            continue

        # remove empty and new-line characters from end
        line = _remove_end_empty(line)

        anno_spacing = len([a for a in line if isinstance(a, _Separator) and a.type == 1])
        space_spacing = len([a for a in line if isinstance(a, _Separator) and a.type == 2])

        if anno_spacing > 0 or space_spacing > 0:
            new_line = _join_similar(line, anno_spacing > 0)

            # remove consecutive repeated elements
            clean = [v for i, v in enumerate(new_line) if i == 0 or v != new_line[i - 1]]

            new_elements.append(_remove_end_empty(clean))

            if store:
                new_elements.append(store)
                store = None

        else:
            # ignore symbol characters, these are usually page numbers
            if len(line) == 1 and all(not c.isalnum() or c.isnumeric() for c in line[0].text):
                continue

            if len(line[0].text.strip()) == 0 and len(line) > 1:
                # weird exception where english comes before swedish
                store = [e for e in line if len(e.text.strip()) > 0]
                continue

            new_elements.append(line)

    return new_elements


def _condensate_two_liners(elements):
    new_elements = []

    for line in elements:
        if not isinstance(line, List):
            new_elements.append(line)
            continue

        # weird exception
        is_one_liner = len(line) == 5 and line[4].text.startswith('actress') \
            or line[0].text.startswith('have you/has (') \
            or len(line) == 5 and line[0].text == 'nen' \
            or len(line) == 6 and line[0].text == 'massmediet, massmedier, massmedierna' \
            or len(line) == 5 and line[0].text == 'na' and line[4].text == 'art museum'\
            or len(line) == 5 and line[0].text == 'na' and line[4].text.startswith('path,')\
            or len(line) == 5 and line[0].text == 'stämt' and line[4].text.startswith('conform,')\
            or len(line) == 5 and line[0].text == 'na' and 'grandmother, step grandmother' in line[4].text

        # two-liners usually have one element, or have two and a closing parenthesis
        if not is_one_liner and len(line) > 1 and not (len(line) == 2 and line[1].text == ')'):
            new_elements.append(line)
            continue

        last_inserted_elem = new_elements[-1][-1]

        # remove new line hyphen on previous line
        if last_inserted_elem.text.endswith('-'):
            last_inserted_elem.text = last_inserted_elem.text[:-1]
            new_elements[-1] = _join_similar(new_elements[-1] + line, True, False)
        else:
            new_elements[-1] = _join_similar(new_elements[-1] + [_Separator(2)] + line, True)

    return new_elements


def _final_join(elements):
    new_elements = []
    for line in elements:
        if not isinstance(line, List):
            new_elements.append(line)
            continue

        to_store = []

        # weird exceptions
        if line[0].text.startswith('köra (') and len(line) > 7 and isinstance(line[6], _Element) and line[6].text.startswith('in running, i.e'):
            to_store.append(([_Element('köra (kör, körde, kört)', '', 0)],
                             [_Element('to cover (in running, i.e ”to cover a mile”)', '', 0)]))

        elif line[0].text.startswith('Jag skriver till er f'):
            to_store.append(([_Element('Jag skriver till er för att...', '', 0)],
                             [_Element('I am writing to you in order to...', '', 0)]))

            to_store.append(([_Element('Anledningen till att jag skriver är...', '', 0)],
                             [_Element('The reason I’m writing/write is...', '', 0)]))

        elif line[0].text.startswith('jag har alltid varit intresserad'):
            to_store.append(([_Element('jag har alltid varit intresserad av...', '', 0)],
                             [_Element('I have always been interested in...', '', 0)]))

            to_store.append(([_Element('jag är mycket intresserad av...', '', 0)],
                             [_Element('I am very interested in...', '', 0)]))

        else:
            # if there is an ANNO SP use that
            s = [(i, e) for i, e in enumerate(line) if isinstance(e, _Separator) and e.type == 1]
            if len(s) > 0:
                pos = s[0][0]
            else:
                # it's the last separator that separates languages usually
                s = [(i, e) for i, e in enumerate(line) if isinstance(e, _Separator)]
                pos = s[-1][0]

            swedish = [e for e in line[:pos] if isinstance(e, _Element)]
            english = [e for e in line[pos + 1:] if isinstance(e, _Element)]

            to_store.append((swedish, english))

        for elem in to_store:
            part1 = ''
            for e in elem[0]:
                if len(part1) > 0 and not (part1.endswith('(') or e.text.startswith(')')):
                    part1 += ' ' + e.text
                else:
                    part1 += e.text

            part2 = ''
            for e in elem[1]:
                if len(part2) > 0 and not (part2.endswith('(') or e.text.startswith(')')):
                    part2 += ' ' + e.text
                else:
                    part2 += e.text

            new_elements.append((part1.strip(), part2.strip()))

    return new_elements


def _clean(elements):
    new_elements = []

    for line in elements:
        if not isinstance(line, Tuple):
            new_elements.append(line)
            continue

        # happens when english part has spaces
        if line[1].strip().startswith(')'):
            new_elements.append((line[0] + ')', line[1].strip()[1:].strip()))
            continue

        if len(line) == 1:
            raise Exception()

        new_elements.append(line)

    return new_elements


def _create_pairs(elements):
    pairs = []

    for line in [(i, e) for i, e in enumerate(elements)]:
        if not isinstance(line[1], Tuple):
            continue

        swedish = line[1][0]
        swedish_conjugation = None
        english = line[1][1]

        if '(' in swedish and ')' in swedish:
            match = re.match(r'(.*)\((.*)\)(.*)', swedish)
            part1 = match.group(1)
            part2 = match.group(2)
            part3 = match.group(3)

            swedish = ' '.join((part1 + ' ' + part3).strip().split())
            swedish_conjugation = ' '.join(part2.strip().split())

        if bool('(' in swedish) ^ bool(')' in swedish) or bool('(' in english) ^ bool(')' in english):
            raise Exception()

        chapter = [e for e in elements[:line[0]] if isinstance(e, _Marker) and e.type in (0, 2)][-1]

        # handle special classroom phrases
        if chapter.type == 2:
            pairs.append(Pair(None, None, swedish, swedish_conjugation, english))
            continue

        # get page; can be start-of-chapter undefined page as well
        page = [e for e in elements[:line[0]] if isinstance(e, _Marker) and e.type == 1]
        page = None if len(page) == 0 else str(page[-1].val)

        pairs.append(Pair(str(chapter.val), page, swedish, swedish_conjugation, english))

    return pairs


def get_pairs(file):
    elements = _proccess_pdf(file)

    elements = _detect_marker_elems(elements)
    elements = _cleanup_lines(elements)
    elements = _condensate_two_liners(elements)
    elements = _final_join(elements)
    elements = _clean(elements)

    return _create_pairs(elements)
