import genanki
import html


swe_eng_front_template = \
    '''
<div>
    {{Swedish}}
</div>

<div class="mini">
    {{#Chapter}}Kapitel {{Chapter}}{{/Chapter}}<br>
    {{#Text}}<b>{{Text}}</b>{{/Text}}
</div>
'''

swe_eng_back_template = \
    '''
{{FrontSide}}

<hr id=answer>

{{English}}    
'''

eng_swe_front_template = \
    '''
<div>
    {{English}}
</div>

<div class="mini">
    {{#Chapter}}Kapitel {{Chapter}}{{/Chapter}}<br>
    {{#Text}}<b>{{Text}}</b>{{/Text}}
</div>
'''

eng_swe_back_template = \
    '''
{{FrontSide}}

<hr id=answer>

<div>
    {{Swedish}}
</div>
'''

style = \
    '''
.card {
    font-family: arial;
    font-size: 22px;
    text-align: center;
}

.mini {
    margin-top: 20px;
    font-size: 12px;
}
'''


class SwedishNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for(self.fields[0], self.fields[2], '24752456')


my_model = genanki.Model(
    3451223457,
    'Word',
    fields=[
        {'name': 'Swedish'},
        {'name': 'English'},
        {'name': 'Chapter'},
        {'name': 'Text'},
    ],
    templates=[
        {
            'name': 'SWE -> ENG',
            'qfmt': swe_eng_front_template,
            'afmt': swe_eng_back_template,
        },
        {
            'name': 'ENG -> SWE',
            'qfmt': eng_swe_front_template,
            'afmt': eng_swe_back_template,
        }
    ],
    css=style)


def create_deck(name, pairs, output):
    my_deck = genanki.Deck(
        abs(hash(name)) % (10 ** 8) * 98294,
        name
    )

    for pair in pairs:
        tags = [f'Kapitel{pair.chapter}']

        if pair.text:
            tags.append(pair.text.title().replace(' ', ''))

        note = SwedishNote(
            model=my_model,
            fields=[
                html.escape(pair.swedish),
                html.escape(pair.english),
                pair.chapter if pair.chapter else '',
                pair.text if pair.text else ''
            ],
            tags=tags
        )
        my_deck.add_note(note)

    genanki.Package(my_deck).write_to_file(output)
