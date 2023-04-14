from ordkort.process_pdf import get_pairs
from ordkort.deck_creator import create_deck


def main(b1_file, b2_file):
    if b1_file:
        b1_pairs = get_pairs(b1_file, True)
        create_deck('Rivstart B1+B2 (ordkort)', b1_pairs, 'rivstart_b1b2_ordkort.apkg')

    if b2_file:
        b2_pairs = get_pairs(b2_file, True)
        create_deck('Rivstart B2+C1 (ordkort)', b2_pairs, 'rivstart_b2c1_ordkort.apkg')


main('ordkort_b1b2.pdf', 'ordkort_b2c1.pdf')
