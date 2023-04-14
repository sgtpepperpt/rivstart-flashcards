# rivstart-flashcards

Generate Anki decks for Rivstart's ordlistor (A1+A2 & B1+B2) and ordkort (B1+B2 & B2+C1).
The translations for the ordkort are provided by Google Translate.

You can get the PDFs from [Natur & Kultur](https://www.nok.se/rivstart).


## How to use

1. Put PDF files into the root directory. Name them ordlista_a1a2.pdf and ordlista_b1b2.pdf, and ordkort_b1b2.pdf and ordkort_b2c1.pdf.
1. Run `python src/ordlista.src` to create decks from the Ordlistor.
1. Run `python src/ordkort.src` to create decks from the Ordkort.
1. Open output Anki decks to add them to the app.
