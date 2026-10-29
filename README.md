# Recombee Movies

Proiect pentru laboratoarele 2 și 3 de Sisteme de Recomandare. Am folosit Python și SDK-ul oficial Recombee pentru a defini proprietățile unui catalog de filme și a încărca produsele în platformă.

## Dataset și proprietăți

Am folosit [Movies Dataset de pe Kaggle](https://www.kaggle.com/datasets/akshaydattatraykhare/movies-dataset), publicat de Akshay Dattatray Khare, cu date din TMDb. Fișierul [`archive-3/tmdb_5000_movies.csv`](archive-3/tmdb_5000_movies.csv) conține **4.803 filme**, în limita cerută de 100–10.000. Am păstrat CSV-ul original; scriptul validează câmpurile folosite înainte de import.

Coloana `id` devine identificatorul nativ **`itemId`** în Recombee și nu este înregistrată ca proprietate separată.

| Proprietate | Tip Recombee |
| --- | --- |
| `title` | `string` |
| `original_language` | `string` |
| `budget` | `int` |
| `revenue` | `int` |
| `popularity` | `double` |
| `vote_average` | `double` |
| `vote_count` | `int` |

## Implementare

- [`recombee_properties.py`](recombee_properties.py) — laboratorul 2: validează CSV-ul și înregistrează cele șapte proprietăți.
- [`recombee_items.py`](recombee_items.py) — laboratorul 3: convertește valorile, mapează ID-urile și trimite filmele prin `SetItemValues`, cu `cascade_create=True`, în loturi `Batch` de maximum 100.

Importul folosește **49 de loturi**: 48 × 100 și ultimul cu 3 filme. Scriptul verifică fiecare răspuns din lot, apoi citește catalogul paginat și compară toate ID-urile și proprietățile cu CSV-ul. Reluarea importului actualizează aceleași ID-uri, fără duplicate.

## Rulare

```bash
git clone https://github.com/Antonio0805/recombee-movies.git
cd recombee-movies
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Pe Windows activez mediul cu `.\.venv\Scripts\Activate.ps1`.

Păstrez configurația `.env` de la laboratorul 2. La o instalare nouă, copiez `.env.example` în `.env` și completez `RECOMBEE_DATABASE_ID`, `RECOMBEE_PRIVATE_TOKEN` și `RECOMBEE_REGION` din contul Recombee. Tokenul și mediul virtual sunt excluse din Git.

```bash
python recombee_items.py --dry-run          # Validare locală
python recombee_properties.py              # Creează proprietățile lipsă
python recombee_items.py                   # Import și verificare completă
python recombee_items.py --verify-only     # Verificare fără scriere
```

## Rezultate verificate

Pe **29 octombrie 2026**, cele **4.803 filme au fost încărcate cu succes în Recombee**. Verificarea prin API a confirmat toate cele **33.621 de valori** ale proprietăților. Am verificat și vizual în **Admin UI → Development → Items**: apar 4.803 item-uri, cu atributele completate. Accesul profesorului configurat la laboratorul 2 se păstrează.

Raportul se salvează local în `reports/recombee_items.json`. Toate cele **22 de teste** au trecut:

```bash
python -m unittest discover -s tests -v
```

Cerințele și codul de pornire: [GG-Academy — laboratorul 3](https://github.com/GG-Academy/Recommender-Systems/tree/main/lab03). Documentație: [Recombee API](https://docs.recombee.com/api).

Dataset-ul folosește API-ul TMDb și nu este aprobat sau certificat de TMDb. Pagina Kaggle indică licența „Other (specified in description)”.
