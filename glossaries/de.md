# EXAPUNKS – Deutsches Glossar (starting point)

This is a **starting point** for a German term ledger, distilled from a complete German fan
translation. The skill copies it to `workspace/de/glossary.md`; from then on that copy is
*your* binding ledger. Extend it as you go (new terms from translator notes, decisions from
reviews). It deliberately contains **no game text**: only term mappings, names and
conventions. Where a convention concerns full sentences (catchphrases, standard briefing
phrasings, zine article titles), it is described here and you fill in your own table.

**Rule for every translator and reviewer:** look up every non-standard term here before
translating it. If a term is missing, pick a rendering, use it consistently and record it
in `notes/newterms-<agent>.md` so it can be merged. Never introduce a second rendering for
a term that is listed.

## 0. Tone & voice

A cyberpunk hacker story in a slightly-off 1997 dystopia: a sick hacker (Moss) relearns
their craft for a strange AI (EMBER-2), while an underground hacker scene chats on the side.
Keep it **cool, dry, a little bleak, a little funny**. The hero is a quiet legend, the world
is rotten, the hacking is the fun part. Natural, contemporary, spoken German, no
translationese. Short lines stay short.

| Character | Voice in German |
|---|---|
| **EMBER-2** | Curious AI, slightly stilted and clinical but playful, sometimes creepily cheerful. Correct German, likes technical words, deadpan humour. Its short status words are fixed catchphrases (§3). |
| **Moss** (player) | Terse, dry, weary, occasionally sarcastic. Narration lines (speaker Moss describing what happens) are first person, present tense. |
| **Nivas** | Street-smart courier and hustler; casual and friendly („Hey“, „Na ja“, „echt“). |
| **Ghast** | Older hacker and zine editor; idealistic, melancholic, a mentor. Warm but tired. |
| **Isadora** | Old friend; kind, harried, a bit nervous. |
| **Chat** (EXAPUNKS chat room) | Late-90s net kids: **all lowercase** (nouns too) unless the original shouts in CAPS, sloppy punctuation, emoticons as is, net slang („jo“, „krass“, „alter“; „digga“ sparingly). **Reproduce typos with German typos** of comparable kind (when someone later corrects a typo, the correction must still make sense). Ghast types lowercase too, but punctuates properly. |

**Address:** everybody says **„du“** to everybody; plural „ihr“. Briefings address the player with „du“ as well.

## 1. Hard rules

1. **The EXA language stays English**: instructions (`LINK`, `GRAB`, `COPY`, `ADDI`, `SUBI`, `MULI`, `DIVI`, `MODI`, `SWIZ`, `TEST`, `KILL`, `REPL`, `HALT`, `MODE`, `VOID`, `DROP`, `FILE`, `SEEK`, `MARK`, `JUMP`, `TJMP`, `FJMP`, `MAKE`, `WIPE`, `NOOP`, `RAND`, `HOST`, `NOTE`, `@REP`, `@END`…), registers (`X`, `T`, `F`, `M`, `GX`, `GY`, `GZ`, `#NERV`, `#POWR`, `#DATA`…), and keyword values in `‗…‗`. Code listings are copied verbatim; only `NOTE` comments may be translated.
2. **On-screen identifiers stay as the game shows them**: host names in `*…*`, file IDs, hardware abbreviations (CNS, ARM, HND, V-CTX, SA-N, AV-N…). In text-only mode, UI button labels quoted in briefings stay English in ASCII quotes; in UI mode `tools/ui.py relabel` swaps in the German labels.
3. **Speaker names and chat handles are never translated** (EMBER-2, Moss, Nivas, Ghast, Isadora, SYSTEM, deadlock, mutex8021, plastered, x10x10x, hydroponix, NthDimension, selenium_wolf, nivas_d). In chat lines they are written lowercase as in the original, including nicknames.
4. **Markup survives with the same count**: `_kursiv_`, `*fett/Host*`, `{Schimpfwort}`, `<PLATZHALTER>`, escaped `\*` `\_`, indentation, blank lines. The German profanity goes *inside* the braces (the game can censor brace content), and nothing but profanity may sit in braces. A brace may cover a whole compound in German where the English braced only part of a word.
5. **No ASCII `"` inside dialogue.** Use „…“ (inner ‚…‘), typographic apostrophe ’, keep the original's ellipsis style.
6. **Branches:** a `↳ alt` line is an alternative to the line above. A run of alternatives = player choices (first line is Moss) or responses, **matched by position** across the following alternative groups. Read every path as its own conversation.
7. **Gender:**
   - **Moss** is never gendered: no gendered pronouns, articles, nouns or adjective endings for Moss. Rephrase („richtig gut im Hacken“ instead of a gendered noun). „Mensch“ is fine.
   - **Nivas** is non-binary: use **no pronoun**. Repeat the name or restructure the sentence.
   - Ghast = er. Isadora = sie. EMBER-2: avoid pronouns; „die KI“ if unavoidable.
8. **Length:** German runs ~30 % longer. Player choices (Moss lines and their alternatives) are buttons: keep them short and punchy.

## 2. Names that stay as they are

TRASH WORLD NEWS (the zine; short: TRASH WORLD), EXAPUNKS (chat room / scene), Last Stop (convenience-store chain), Peanut Blast, Corn Rush, Euclid’s Pizza, Zebros (copy shop), Sawayama WonderDisc, TEC Redshift, Equity First (Bank), Workhouse, Digicash, King’s Ransom Online, Haxtasy, chatsubo, Axiom, SnaxNet, FEMA, DARPA, SSEA, ME2U, PROJECT OGRE, EXODUS, CHATSUBO, KGOG-TV, Valhalla, Holman Dynamics, Cybermyth Studios, Warehouse 27, Mitsuzen, NETronics, Bloodlust Online, ПАСЬЯНС, HACK*MATCH.
Deliberate misspellings of names in chat stay misspelled. The in-game pop song title and its lyrics stay English (it is an English radio hit in the story).

## 3. Fixed phrases (EMBER-2 catchphrases & recurring words)

EMBER-2 has a handful of one- or two-word status remarks it repeats across the whole game.
Fix one rendering each and never vary it. Starting set:

| English | German |
|---|---|
| Processing. | Verarbeitung läuft. |
| Still processing. | Verarbeitung läuft noch. |
| Recalibrating. | Rekalibrierung läuft. |
| Interesting. | Interessant. |
| Fascinating. | Faszinierend. |
| Hypothesis: … | Hypothese: … |
| (good) data / the corpus | (gute) Daten / der Korpus |
| positive encouragement | positive Bestärkung |
| prefrontal cortex | präfrontaler Cortex |
| in the wild | in freier Wildbahn |
| hack (verb / noun) | hacken / das Hacken; der Hack (a single job) |

Add EMBER-2's other recurring short sentences (e.g. its "let's move on" line, its "I have grown" line) to your own copy of this table the first time you meet them.

## 4. Terminology

| English | German | Notes |
|---|---|---|
| EXA / EXAs | der EXA / die EXAs | genitive „des EXAs“ |
| AI / AI construct | KI (die) / KI-Konstrukt | |
| hacker | Hacker | avoid the singular noun for Moss (gender rule) |
| hacker battle | das Hacker-Battle (pl. -Battles) | as in Rap-Battle |
| tournament | Turnier | |
| zine | das Zine (pl. Zines); as an object: das Heft | |
| issue (of the zine) | Ausgabe | |
| the phage | der Phage | „gegen den Phagen“, „des Phagen“ |
| medication / dose | Medikament(e) / Dosis | bootleg → Schwarzmarkt-/gefälschte Medikamente |
| pharm | Pharmafarm | |
| dataphone | das Dataphone (pl. Dataphones) | |
| wardialer / wardialing | Wardialer / Wardialing (wardialen) | |
| lurk | mitlesen; chat slang „lurken“ | |
| chat room | Chatroom | |
| rig | Rig / Rechner | |
| dev kit | Devkit / Entwicklungskit | |
| region lock / region code | Regionalsperre / Regionalcode | |
| network / host / link | Netzwerk / der Host (pl. Hosts) / der Link | |
| file / file ID | Datei / Datei-ID („Datei 200“) | |
| register / hardware register | das Register / Hardware-Register | |
| instruction | Befehl („KILL-Befehl“) | |
| pseudo-instruction | Pseudobefehl | |
| operand | Operand | |
| label (MARK target) | das Label | not „Sprungmarke“ |
| keyword (data type) | Schlüsselwort | values stay English |
| value | Wert | |
| cycle | Zyklus (pl. Zyklen) | |
| test run | Testlauf | |
| task | Aufgabe | |
| solution | Lösung | |
| leave no trace | keine Spuren hinterlassen | as a named requirement in _italics_ |
| terminate (an EXA) | beenden | |
| grab / drop (a file) | greifen / ablegen (fallen lassen) | |
| traverse (a link) | durchqueren | |
| file cursor / file pointer | Dateicursor | |
| held file | gehaltene Datei | |
| global / local mode | globaler / lokaler Modus | |
| swizzle | swizzeln / Swizzle-Maske | |
| loop / conditional jump | Schleife / bedingter Sprung | |
| step through (debugger) | durchsteppen | |
| chunk (legacy storage) | der Chunk (pl. Chunks) | |
| offset | Offset | |
| node | Knoten | network nodes → Netzwerkknoten |
| nerve / median nerve / optic nerve | Nerv / Medianusnerv / Sehnerv | |
| visual / cerebral cortex | visueller / zerebraler Cortex | |
| sinoatrial / atrioventricular node | Sinusknoten / Atrioventrikularknoten | |
| central nervous system (CNS) | zentrales Nervensystem (CNS) | |
| human-machine interface | Mensch-Maschine-Schnittstelle | |
| modem / sandbox / hotfix | Modem / Sandbox / Hotfix | |
| debug | debuggen | |
| virtual machine | virtuelle Maschine | |
| packet / checksum / packetize | Paket / Prüfsumme / in Pakete zerlegen | |
| warez | Warez | |
| ATM | Geldautomat | |
| checking account | Girokonto | |
| shell company | Briefkastenfirma | |
| back-pay | Nachzahlung | |
| directory (file) | Verzeichnis | |
| call number (library) | Signatur | |
| substation | Umspannwerk | |
| drive array | Laufwerks-Array | |
| highway sign | Autobahnschild | |
| restaurant guide | Restaurantführer | never just „der Führer“ |
| convenience store / store location | Minimarkt, Ladenkette / Filiale | |
| receipts (data entry job) | Belege | |
| copy shop | Copyshop | |
| cult | Sekte | |
| heist | Coup | |
| artificial scarcity | künstliche Verknappung | |
| arcade cabinet | Automat | |
| solitaire | Solitär | |
| pirated | raubkopiert | |
| frame rate | Bildrate | |
| processing power | Rechenleistung | |
| self-interest | Eigennutz | |
| outlier | Ausreißer | |
| agency (free will) | Handlungsfreiheit / Selbstbestimmung | |
| raided | hochgenommen | |
| eat (an AI absorbing another) | aufessen | |
| transfer (mind upload) | Übertragung | |
| personals ad | Kontaktanzeige | |
| placeholder | Platzhalter | |
| dial-up connection | Einwahlverbindung | |
| compass directions | N/O/S/W | |
| courier (Nivas) | avoid the masculine „Kurier“ for Nivas; rephrase („liefert aus“) | |
| champ (said to Moss) | gender-neutral alternative, e.g. „Sportskanone“ | |

**Formats:** money „75 $“, „1,00 $“, „10.000 $“; dates „Mo 01.12.97 09:05“ (weekday abbreviation, DD.MM.YY, 24 h); EMBER-2's X → „X von EMBER-2“ (no genitive -s on the name).

## 5. Recurring sentence conventions (fill in your own tables)

- **Zine article titles** are quoted verbatim in the briefings and must match the German manual exactly. Keep a table English title → German title in your glossary copy and use it everywhere (briefings, manual table of contents, article headings). The "for more information see X in issue N of the zine" reference recurs in many briefings: decide one German sentence pattern and reuse it.
- **Briefing standard phrasings** (the "leave no trace isn't required" note, "file N contains…", the scoring rules in battles, "note that…") recur in many briefings. Decide each German phrasing once, list it here, and reuse it word for word. Imperative du-form (invented example: „Verschiebe Datei 123 in den Host *beispiel*.“). Always „in den Host *x*“ / „im Host *x*“.
- **SYSTEM chat messages** (someone connects, disconnects, waves) recur; fix one German pattern each.

## 6. User interface (strings.csv and redrawn textures)

| English | German |
|---|---|
| Show Goal / SHOW GOAL | Ziel zeigen / „ZIEL ZEIGEN“ |
| Test Run / Test Runs | Testlauf / Testläufe |
| Test Run Complete | Testlauf abgeschlossen |
| SELECT OPPONENT | GEGNER WÄHLEN |
| Reset / Pause / Step / Run / Fast-forward | Zurücksetzen / Pause / Schritt / Ausführen / Vorspulen |
| Cycles / Size / Activity (scores) | Zyklen / Größe / Aktivität |
| Points / Win Count / Storage Limit | Punkte / Siege / Speicherlimit |
| Opponent / You | Gegner / Du |
| Task Complete | Aufgabe erledigt |
| Histograms | Histogramme |
| Battle Won / Lost / Drawn | Sieg / Niederlage / Unentschieden |
| Wins / Draws / Losses | Siege / Remis / Niederlagen |
| Edit / Test / Copy / Delete / Open / Export | Bearbeiten / Testen / Kopieren / Löschen / Öffnen / Exportieren |
| Options / Controls / Back | Optionen / Steuerung / Zurück |
| Exit Game | Spiel beenden |
| Tasks / Chat | Aufgaben / Chat |
| Mark as Complete | Als erledigt markieren |
| Meeting with X | Treffen mit X |
| Profanity (Show / Hide) | Schimpfwörter (Anzeigen / Ausblenden) |
| Unsolved / Solved | Ungelöst / Gelöst |
| Point-of-sale System | Kassensystem |
| Order / Sales / Accounting / Scheduling / Ticketing System | Bestell- / Vertriebs- / Buchhaltungs- / Termin- / Ticketsystem |
| Player Database | Spielerdatenbank |
| Drive Controller | Laufwerkscontroller |
| Development Kit | Entwicklungskit |
| Unknown Network | Unbekanntes Netzwerk |
| hotkeys | Strg, Umschalt, Esc, Klick; Alt, Cmd, Tab, Enter, F-keys unchanged |
| IN / OUT (hardware port labels) | IN / OUT (kept) |
| WorkHouse buttons SUBMIT / CANCEL / DISCONNECT / EXIT / OKAY | ABSENDEN / ABBRECHEN / TRENNEN / BEENDEN / OKAY |
