from ordlista.process_pdf import get_pairs
from ordlista.deck_creator import create_deck


def main(a1_file, b1_file):
    if a1_file:
        a1_pairs = get_pairs(a1_file)
        create_deck('Rivstart A1+A2', a1_pairs, 'rivstart_a1a2.apkg')

    if b1_file:
        b1_pairs = get_pairs(b1_file)
        create_deck('Rivstart B1+B2', b1_pairs, 'rivstart_b1b2.apkg')


main('ordlista_a1a2.pdf', 'ordlista_b1b2.pdf')
