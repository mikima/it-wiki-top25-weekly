# Note operative per agenti (Codex, Claude Code…)

Le regole di scrittura delle descrizioni sono in `agent-instructions.md`, lo
stesso testo usato da `enrich_descriptions_openai.py`. Queste note servono solo
a chi aggiorna i file a mano o con un agente.

- Non modificare le voci con `"description_source": "manual"`.
- Quando scrivi una descrizione, imposta `"description_source": "openai"` (o il
  nome dello strumento) e, se lo conosci, `"description_model"`.
- Il `google_news_url` nel JSON spesso porta alla pagina di consenso di Google e
  non ai risultati. Per controllare i titoli della settimana funziona meglio il
  feed RSS di Google News con query del tipo
  `NOME_VOCE after:YYYY-MM-DD before:YYYY-MM-DD`.
- Prima di modificare `docs/json/YYYY-WW.json`, rileggi sempre il file
  corrente: può essere stato già ritoccato.
- Se devi aggiornare molte `description` insieme, cambia solo il campo
  `description` con una riscrittura strutturata del JSON (non patch testuali).
  Rigenerare il file con `wiki-get-top-weekly-pages.py` conserva le descrizioni
  manuali.
- Dopo ogni aggiornamento valida il JSON (`json.loads(...)`); se il file è un
  output `--top 30`, controlla che gli articoli restino 30.
