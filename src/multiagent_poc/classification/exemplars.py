"""Reference utterances per intent, used to build the nearest-neighbor
intent classifier (see classifier.py).

Deliberately distinct wording from docs/test_questions.md — that file is the
held-out evaluation set. Reusing its phrasing here would leak the eval set
into the classifier's own reference data and inflate accuracy numbers.

No exemplars for Intent.INNE: the classifier only ever predicts one of the 8
process categories. "inne" is not something we teach it to recognize — it's
what the confidence gate falls back to when nothing matches confidently
(see gate.py). Indexing negative/junk exemplars under "inne" would just make
the gate's job harder to reason about.
"""

from multiagent_poc.intents import Intent

INTENT_EXEMPLARS: dict[Intent, list[str]] = {
    Intent.DOSTAWY: [
        "Nie zgadza się liczba palet na liście przewozowym.",
        "Kierowca zostawił mniej skrzynek niż było na WZ.",
        "Produkty chłodzone przyjechały w za wysokiej temperaturze.",
        "Dostawa się spóźnia, minęła już godzina okna czasowego.",
        "Karton z towarem jest wilgotny i uszkodzony przy odbiorze.",
        "Czy mogę odmówić przyjęcia całej palety?",
    ],
    Intent.REKLAMACJE: [
        "Klient zwraca otwarte opakowanie i chce zwrotu pieniędzy.",
        "Produkt spożywczy okazał się zepsuty po otwarciu w domu.",
        "Klient reklamuje słuchawki kupione tydzień temu, nie działają.",
        "Jak przyjąć reklamację bez paragonu?",
        "Klient twierdzi, że produkt był uszkodzony już na półce.",
        "Czego nie wolno robić przy reklamacji produktu niespożywczego?",
    ],
    Intent.PLATNOSCI: [
        "Terminal odrzuca każdą płatność kartą od rana.",
        "Nie zgadza się stan gotówki przy zamknięciu zmiany.",
        "Klient płacił BLIK-iem, ale transakcja nie pojawiła się w systemie.",
        "Jak rozliczyć nadwyżkę w kasie na koniec dnia?",
        "Voucher promocyjny nie chce się zeskanować przy kasie.",
        "Podejrzewam, że klient próbuje zapłacić skradzioną kartą.",
    ],
    Intent.BHP: [
        "Pracownik skaleczył się nożem podczas krojenia pieczywa.",
        "Rozlana chemia czyszcząca na podłodze w magazynie.",
        "Jak zgłosić wypadek przy pracy?",
        "Pracownik poślizgnął się na mokrej podłodze przy wejściu.",
        "Czy muszę zgłaszać drobne otarcie przy rozładunku?",
        "Zepsuta osłona na maszynie do krojenia wędlin.",
    ],
    Intent.HR: [
        "Chcę zamienić się zmianą z koleżanką w przyszłym tygodniu.",
        "Kiedy zostanie zatwierdzony mój wniosek urlopowy?",
        "Nie zgadza się liczba nadgodzin na moim pasku wypłaty.",
        "Jak zgłosić nieobecność chorobową kierownikowi?",
        "Czy grafik na przyszły miesiąc jest już opublikowany?",
        "Chciałbym złożyć wypowiedzenie, jaka jest procedura?",
    ],
    Intent.HIGIENA: [
        "Termometr w lodówce pokazuje wyższą temperaturę niż powinien.",
        "Jak przygotować się do kontroli sanepidu?",
        "Produkty z krótkim terminem przydatności leżą za nowymi na półce.",
        "Czy muszę wypełniać kartę kontroli temperatur codziennie?",
        "Zauważyłem ślady szkodników w magazynie.",
        "Procedura mycia rąk i stanowiska pracy przy obsłudze żywności.",
    ],
    Intent.AWARIE_TECHNICZNE: [
        "Kasa fiskalna zawiesza się i nie drukuje paragonów.",
        "Internet w sklepie nie działa od rana, terminal offline.",
        "Lodówka z napojami przestała chłodzić.",
        "Jak zgłosić awarię klimatyzacji w punkcie sprzedaży?",
        "Drukarka etykiet cenowych się zacięła.",
        "System kasowy pokazuje błąd i nie da się zalogować.",
    ],
    Intent.SKARGI_KLIENTA: [
        "Klient podnosi głos i grozi napisaniem skargi do centrali.",
        "Klient jest niezadowolony z obsługi i żąda rozmowy z kierownikiem.",
        "Spór o cenę produktu, która różni się od tej na półce.",
        "Klient zachowuje się agresywnie wobec kasjera.",
        "Jak uspokoić sytuację, gdy klient robi awanturę przy kasie?",
        "Klient grozi, że nagra sytuację i wrzuci do internetu.",
    ],
}
