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
- usa i link già presenti nel JSON, soprattutto google_news_url e article_url, per capire il fatto associato al picco
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
