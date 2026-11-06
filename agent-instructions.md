Scrivi la descrizione di ogni voce della classifica settimanale delle pagine più viste di Wikipedia in italiano.

Obiettivo: ancorare nel tempo il motivo del picco di visite. Quasi sempre il picco ha una causa puntuale (una morte, una trasmissione televisiva, una partita, un'uscita al cinema o su una piattaforma, un anniversario, una notizia): trovala e datala. Più raramente il picco è un errore nei dati oppure non ha una causa riconoscibile: in quei casi dillo in modo chiaro e breve.

## Forma

- Una frase, al massimo due se la seconda aggiunge un fatto utile (ad esempio un collegamento con un'altra voce).
- Breve: di solito tra 60 e 160 caratteri.
- Italiano semplice e asciutto, tono fattuale, presente storico ("muore", "vince", "va in onda").
- Testo semplice: niente link, niente markup, niente virgolette tipografiche superflue.
- Le date si scrivono "il 4 marzo", "il 13 e il 14 febbraio", "dal 9 al 15 maggio". **Non aggiungere l'anno** alle date quando coincide con quello della settimana; scrivilo solo se è diverso ("morto nel 2017", "uscito nel 1997"). L'anno resta invece quando fa parte di un nome proprio ("Pallone d'oro 2026", "Elezioni politiche italiane del 2018").
- **Contesto pensato per chi legge in Italia**: dai il contesto minimo che serve a capire a chi non conosce il soggetto. Per figure e temi molto noti in Italia basta poco; per figure straniere o di nicchia (politica estera, sport meno seguiti, personaggi di altri paesi) aggiungi ruolo, partito o coalizione, squadra, carica. Sintetico sì, ma senza togliere ciò che serve a capire il fatto.
- **Chiama eventi e organizzazioni con il loro nome**: il partito o la coalizione, il tipo di elezione (presidenziali, parlamentari, ballottaggio), l'edizione del premio o del torneo, il titolo del programma. Evita perifrasi come "una coalizione avversaria di…" o "le notizie successive alle elezioni".

Due strutture possibili:
1. **Soggetto, fatto datato** — **sempre per le persone** (anche concorrenti, ospiti, parenti: professione, nazionalità o ruolo che spiega chi sono), e per tutto ciò che va presentato. Prima il contesto, poi il fatto. Per le persone morte aggiungi in breve perché erano note.
   - "Attore e artista marziale statunitense, muore il 20 marzo a 85 anni."
   - "Film del 2009 diretto da Quentin Tarantino, va in onda su Italia 1 il 31 luglio."
2. **Fatto datato in apertura** — solo per opere, puntate, eventi, ricorrenze e simili, quando il soggetto è chiaro dal titolo e quello che conta è il fatto. Non per le persone.
   - "Il 29 dicembre viene distribuita su Netflix la quarta stagione della serie."
   - "Il 3 giugno vince la finale di Champions League contro la Juventus."

## Come trovare il motivo

- Usa i dati forniti: "daily_views" e "segnali_picco" dicono quando cade il picco; "context.news" e "context.wikipedia_summary" dicono cosa è successo. Cerca il fatto nel giorno del picco o in quello precedente.
- **Pensa sempre alla televisione**: film trasmessi in prima serata (Rai 1, Canale 5, Italia 1, Rai 3, Iris…), puntate di reality e talent (concorrenti, giudici, ospiti), ospitate nei talk show, fiction e serie, quiz televisivi le cui domande spingono a cercare una voce. Quando è possibile indica canale e puntata: "Concorrente della seconda edizione del Grande Fratello VIP, la cui settima puntata va in onda il 23 ottobre su Canale 5."
- **Puntate televisive**: non raccontare la trama. Indica canale, data e, se identificabile, il numero della puntata o dell'episodio ("la quinta puntata", "il nono e il decimo episodio", "l'ultima puntata").
- **Collega le voci tra loro**: guarda "classifica_della_settimana". Se il picco dipende da un'altra voce in lista, dillo esplicitamente (un parente, un film, un luogo, un'organizzazione legati a un fatto principale).
  - "Loggia massonica chiusa nel 1982 perché considerata eversiva. Il picco è probabilmente legato alla morte di Licio Gelli, suo «Maestro venerabile», il 15 dicembre."
  - "Attore italiano morto nel 2017, il picco è probabilmente legato al film Fabrizio De André - Principe libero, andato in onda il 13 e il 14 febbraio su Rai 1, in cui viene raccontata la sua amicizia con il cantante."
- **Continuità**: guarda "classifica_settimana_precedente" e "settimane_consecutive_precedenti_in_lista". Se la voce è la coda di un evento della settimana prima, fai riferimento a quell'evento; se resta in lista da molte settimane, puoi dirlo.
  - "Serie televisiva statunitense pubblicata su Netflix il 31 marzo, è la decima settimana di seguito tra le pagine più viste."
  - "Il picco di visite si è verificato la settimana precedente, con la finale di Coppa Italia del 17 maggio vinta dalla Juventus."
- Ricorrenze e anniversari valgono come causa: "Il 23 novembre cade il 25° anniversario della morte del cantante."; anche i Doodle di Google.

## Quando non c'è un motivo sicuro

Scegli uno di questi esiti, senza riempire lo spazio con frasi generiche:

- **Ipotesi**: se c'è un fatto plausibile ma non certo, usa "probabilmente legato a", "forse in relazione a", "potrebbe essere legato a", sempre seguito da un fatto preciso e datato.
  - "Picco di visite il 7 luglio, forse in relazione all'avvistamento di lupi nei pressi di Borgo a Buggiano, in provincia di Pistoia."
  - "Rete televisiva italiana, il picco del 20 aprile potrebbe essere legato alla quarta puntata del serale di Amici."
- **Nessun picco**: se le visite sono stabili nella settimana (nessun giorno spicca sugli altri), non attribuire la presenza in classifica a una singola notizia minore. Per voci sempre presenti (Italia, reti televisive, calendari) basta una frase breve; per gli altri temi dai il contesto e, se c'è, il fatto più rilevante della settimana senza presentarlo come causa certa.
  - "Nessun picco di rilievo, il numero di visite è nella media."
  - "Difficile dire il motivo del picco di visite."
- **Errore nei dati**: se quasi tutte le visite cadono in un solo giorno ("segnali_picco.picco_isolato" è true) **e** nelle notizie non c'è nessun evento che lo spieghi, **e** il soggetto non è legato a una morte, a una trasmissione o a un altro fatto della settimana, scrivi che si tratta probabilmente di un errore e riporta i numeri. Attenzione: anche eventi veri (una morte, un'ospitata in TV) possono concentrare le visite in un giorno; "picco_isolato" è un indizio, non una prova.
  - "Probabilmente un errore nella raccolta dei dati: circa 200 visite al giorno, 137.000 lunedì e poi di nuovo nella media."
  - "Insieme di fogli stampati o manoscritti. Quasi certamente un errore nella raccolta dei dati."

## Da evitare

- Formule sui lettori o psicologiche: "i lettori cercano", "l'interesse nasce da", "la pagina è stata molto cercata", "la curiosità del pubblico".
- Formule vaghe senza un fatto dietro: "torna d'attualità", "è al centro dell'attenzione", "al centro delle ricerche", "oggetto di notizie collegate", "protagonista nelle cronache", "consultato durante", "citato nei servizi", "è citato nelle notizie", "torna nelle notizie", "è coinvolto nelle notizie". Al loro posto scrivi direttamente il fatto ("il 27 ottobre si scusa per…") oppure usa uno degli esiti della sezione precedente.
- Descrivere la curva invece del motivo: "registra un picco di visualizzazioni", "con visualizzazioni distribuite uniformemente", "registra visualizzazioni stabili durante la settimana", "resta tra i titoli principali al botteghino". Il giorno del picco si può citare ("Picco di visite il 5 dicembre, probabilmente…") solo se segue un fatto.
- Contesti ridondanti su soggetti già noti a tutti: "Repubblica parlamentare dell'Europa meridionale e Stato membro dell'Unione europea" → "Stato dell'Europa meridionale" o niente.
- La prima persona ("penso", "non ho idea") e le ipotesi non verificabili.
- L'anno quando coincide con quello della settimana.
- Inventare fatti: se non ci sono elementi, usa uno degli esiti della sezione precedente.

## Esempi

- "Capitano della Fiorentina, il 4 marzo viene trovato senza vita nella stanza d'albergo di Udine che ospitava la squadra prima della partita di Serie A."
- "Film del 2004 diretto da Mel Gibson, va in onda il giorno di Pasqua (16 aprile) su Canale 5."
- "Paese natale di Davide Astori, il calciatore della Fiorentina trovato senza vita il 4 marzo."
- "Figlio di Fabrizio De André, il picco è probabilmente legato al film Fabrizio De André - Principe libero, andato in onda il 13 e il 14 febbraio su Rai 1."
- "Pilota italiano, vince il Gran Premio di Cina il 15 marzo partendo dalla pole position."
- "Una domanda della puntata del 25 gennaio di Chi vuol essere milionario? riguarda questo argomento."
