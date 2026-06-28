Instruction for AI agents to quickly generate descriptions (in italian):

```
Nel file docs/json/XXXX-XX.json, aggiorna il campo description per ogni voce.

Istruzioni:
- scrivi una sola frase per pagina
- tono asciutto, fattuale, senza interpretazioni
- Inizia contestualizzando il soggetto ("Attore norvegese" Soubrette italiana" "Film islandese del 2026" "Isola al largo della costa dell'Iran"). In particolare per persone decedute, aggiungi in breve perchè erano famose.
- Continua spiegando il motivo del picco di visite.
- non usare formule causali o psicologiche come “i lettori cercano”, “l’interesse è dovuto a”, “la pagina è stata vista perché”
- non usare formule vaghe come “torna d’attualità”, “è al centro dell’attenzione”, se puoi sostituirle con un fatto preciso
- quando possibile cita la data precisa dell’evento nella settimana
- Se una pagina ha un andamento abbastanza lineare e un piccolo picco è l'unico caso in cui puoi fare una ipotesi (es. RAI1 "primo canale televisivo, difficile dare una motivazione al picco, potrebbe essere legato al primo episodio di Miss Italia")
- usa i link già presenti nel JSON, soprattutto google_news_url e article_url, per capire il fatto associato al picco. Puoi controllare anche se nella settimana precedente ci fosse già quella voce, in tal caso esplicita la continuità.
- se non c'è proprio una correlazione sicura, resta sul fatto osservabile più vicino nella settimana, oppure usa una formula "anche se non ci sono evidenti prove, potrebbe..."
- mantieni l’italiano semplice e compatto
- se le visualizzazioni sono la coda di un picco creato da un evento precedente, fai riferimento all'evento precedente (es. "Miniserie britannica di Netflix disponibile sulla piattaforma dal 13 marzo 2025.")

Stile desiderato:
- esempio buono: “Film norvegese del 2025, vince l'Oscar al miglior film internazionale il 16 marzo 2026.”
- esempio buono: “Attore e artista marziale statunitense, muore il 20 marzo 2026 a 85 anni.”
- Esempio buono: "Pilota italiano, vince il Gran Premio di Cina il 15 marzo 2026 partendo dalla pole position."
- Esempio buono: "Referendum costituzionale del 2016 sulla riforma Renzi-Boschi. Le ricerche del 23 marzo 2026 sono probabilmente legate al recente voto nel referendum sulla giustizia."
- esempio da evitare: “La pagina è molto cercata perché i lettori vogliono sapere…”
- esempio da evitare: “L’interesse nasce dalla grande attenzione mediatica…”
- esempio da evitare: "Il picco dell'11 marzo riflette le ricerche sul cast e sui personaggi subito dopo il debutto."
- esempio da evitare: "... e resta tra i titoli principali al botteghino nella settimana"

Alla fine:
- salva direttamente il file
- verifica che il JSON sia valido
- non cambiare altri campi
```

Note operative emerse:

- Il `google_news_url` nel JSON spesso porta alla pagina di consenso di Google e non ai risultati. Per controllare i titoli della settimana funziona meglio il feed RSS di Google News con query del tipo `NOME_VOCE after:YYYY-MM-DD before:YYYY-MM-DD`.
- Prima di modificare `docs/json/YYYY-WW.json`, rileggi sempre il file corrente: puo essere stato gia ritoccato dopo il prompt precedente.
- Se devi aggiornare molte `description` insieme e una patch testuale rischia di rompere il JSON, conviene rigenerare prima il file con `python wiki-get-top-weekly-pages.py --exclude-stopwords --format json --top 30 --year YYYY --week WW`, poi cambiare solo il campo `description` con una riscrittura strutturata del JSON.
- Dopo ogni aggiornamento, valida sempre con un parse JSON (`json.loads(...)`); se il file e un output `--top 30`, controlla anche che gli articoli restino 30.
