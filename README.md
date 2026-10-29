# Catalog de filme în Recombee — Laboratoarele 2 și 3

Am realizat un catalog de filme folosind Python, un dataset TMDb de pe Kaggle și SDK-ul oficial Recombee. În laboratorul 2 am definit proprietățile, iar în laboratorul 3 am încărcat filmele cu toate valorile lor.

**Import verificat pe 29 octombrie 2026:** am trimis 4.803 filme în 49 de cereri Batch. Am citit apoi catalogul prin API și am comparat fiecare ID și toate cele șapte proprietăți cu CSV-ul: 4.803 filme verificate, 33.621 de valori conforme, fără item-uri suplimentare.

## 1. Dataset-ul pe care l-am folosit

Am continuat cu [Movies Dataset de pe Kaggle](https://www.kaggle.com/datasets/akshaydattatraykhare/movies-dataset), publicat de Akshay Dattatray Khare. Datele provin din The Movie Database (TMDb).

| Detaliu | Valoare |
| --- | --- |
| Domeniu | Filme; un item reprezintă un film |
| Fișier folosit | [`archive-3/tmdb_5000_movies.csv`](archive-3/tmdb_5000_movies.csv) |
| Volum | 4.803 filme, 20 de coloane |
| ID unic în CSV | `id` |
| ID în Recombee | `itemId`, transmis ca text |

Cele 4.803 filme se încadrează în intervalul cerut, de 100–10.000 de item-uri. Am păstrat CSV-ul original, fără să elimin rânduri sau să redenumesc coloane. Scriptul validează câmpurile folosite înainte de a face orice cerere API: acestea sunt completate și au valori valide. Celulele goale din coloanele nefolosite nu intră în import.

În arhivă se află și `tmdb_5000_credits.csv`, cu distribuția și echipele filmelor. L-am păstrat, dar importul folosește doar fișierul de filme. Valorile zero din bugete sau încasări rămân exact ca în sursă.

## 2. Maparea datelor

Proprietățile sunt aceleași cu cele create în laboratorul 2.

| Coloană CSV | Câmp Recombee | Tip | Exemplu: Avatar |
| --- | --- | --- | --- |
| `id` | `itemId` nativ | identificator text | `"19995"` |
| `title` | `title` | `string` | `Avatar` |
| `original_language` | `original_language` | `string` | `en` |
| `budget` | `budget` | `int` | `237000000` |
| `revenue` | `revenue` | `int` | `2787965087` |
| `popularity` | `popularity` | `double` | `150.437577` |
| `vote_average` | `vote_average` | `double` | `7.2` |
| `vote_count` | `vote_count` | `int` | `11800` |

`string` înseamnă text, `int` număr întreg, iar `double` număr cu zecimale. Convertesc explicit valorile din CSV în aceste tipuri Python înainte de trimitere.

ID-ul este primul argument al cererii `SetItemValues`. Nu îl adaug în dicționarul de proprietăți și nu creez o proprietate separată numită `id` sau `itemId`.

## 3. Ce am implementat

Am păstrat [`recombee_properties.py`](recombee_properties.py) pentru laboratorul 2 și am adăugat [`recombee_items.py`](recombee_items.py) pentru laboratorul 3. Noul script refolosește schema, validarea CSV-ului și configurația din laboratorul 2.

La rularea importului:

1. Citește dataset-ul și verifică numărul de rânduri, ID-urile unice, coloanele necesare și valorile numerice.
2. Pregătește fiecare film cu `itemId` și cele șapte proprietăți.
3. Citește configurația locală și verifică prin `ListItemProperties` că schema există și are tipurile corecte.
4. Construiește cereri `SetItemValues(..., cascade_create=True)` și le grupează în `Batch` de maximum 100.
5. Verifică răspunsul fiecărei cereri din lot. Un răspuns HTTP 200 pentru Batch poate conține erori individuale.
6. Citește întregul catalog cu `ListItems`, în pagini de 1.000, până la pagina goală. Compară toate cele șapte proprietăți ale fiecărui film cu valorile din CSV.
7. Salvează raportul local în `reports/recombee_items.json`. Starea `success` apare numai după verificarea completă.

Dacă paginile încă reflectă actualizarea catalogului, verificarea se poate relua de până la trei ori, cu două secunde între încercări. O diferență de atribut este raportată ca eroare.

### De ce folosesc Batch

Pentru 4.803 filme trimit 48 de loturi a câte 100 și un ultim lot cu 3 filme: **49 de cereri HTTP pentru scriere**, în loc de 4.803. Citirea schemei și verificarea de după import sunt apeluri separate.

Codul esențial este:

```python
requests = [
    SetItemValues(item["itemId"], item["values"], cascade_create=True)
    for item in chunk
]
response = client.send(Batch(requests))
```

`cascade_create=True` creează filmul dacă ID-ul nu există. Dacă reiau importul, același ID este actualizat, fără să apară duplicate. Scriptul nu șterge filme sau proprietăți.

## 4. Pregătirea mediului

Repository-ul continuă proiectul de la laboratorul 2 și păstrează același nume pe GitHub.

```bash
git clone https://github.com/Antonio0805/lab02-recombee-movies.git
cd lab02-recombee-movies
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Dacă am deja proiectul clonat, folosesc `git pull --ff-only` în acel folder pentru a primi noul script.

Pe Windows folosesc `py -m venv .venv`, apoi `.\.venv\Scripts\Activate.ps1`. Dependențele sunt deja enumerate în `requirements.txt`: `recombee-api-client`, `pandas` și `python-dotenv`. Recomand Python 3.11 sau mai nou; verificările acestei versiuni au rulat cu Python 3.9.6 și SDK 6.3.1.

### Configurația Recombee

Păstrez fișierul `.env` configurat la laboratorul 2. Pentru o instalare nouă copiez modelul și completez valorile din **Recombee Admin UI → Settings → API Logins**:

```bash
cp .env.example .env
```

```dotenv
RECOMBEE_DATABASE_ID=completeaza_database_id
RECOMBEE_PRIVATE_TOKEN=completeaza_private_token
RECOMBEE_REGION=eu-west
```

Folosesc baza de dezvoltare și regiunea ei reală. Tokenul privat rămâne în `.env`, care este exclus din Git. Variabilele deja setate în mediu au prioritate față de fișier.

## 5. Rularea pas cu pas

Rulez comenzile din folderul proiectului, cu mediul virtual activ.

**Pasul 1 — Verific datele local:**

```bash
python recombee_items.py --dry-run
```

Această comandă nu cere token și nu face apeluri API. Afișează numărul de filme, primele rânduri, maparea pentru Avatar și planul de 49 de loturi.

**Pasul 2 — Verific proprietățile existente:**

```bash
python recombee_properties.py --verify-only
```

Dacă pornesc cu o bază nouă, creez mai întâi schema folosind `python recombee_properties.py`.

**Pasul 3 — Încarc filmele:**

```bash
python recombee_items.py
```

La sfârșitul unui import reușit apar mesajele:

```text
Lot 49: 3 filme confirmate; progres 4803/4803.
Verificare API reușită: 4803 filme, toate cele 7 proprietăți coincid cu CSV-ul.
Raport salvat: reports/recombee_items.json
```

**Pasul 4 — Pot repeta numai verificarea, fără scriere:**

```bash
python recombee_items.py --verify-only
```

Pentru un CSV aflat în alt folder pot folosi `--dataset CALE_CSV`. Schema celor șapte câmpuri trebuie să rămână aceeași.

## 6. Verificarea în Recombee Admin UI

În [Admin UI](https://admin.recombee.com/) selectez baza **Development**, apoi **Items**. Verific numărul de item-uri și faptul că rândurile au valori completate. Pentru un exemplu concret, caut `19995` și verific filmul Avatar cu valorile din tabelul de mai sus. Proprietățile pot fi văzute și din **Manage properties**.

Am verificat și vizual pagina **Items** pe 29 octombrie 2026: afișează **4.803 item-uri**, cu ID-urile și cele șapte proprietăți completate în tabel.

Accesul profesorului, configurat la laboratorul 2 cu dreptul **Edit** pe baza folosită, se păstrează.

## 7. Teste și rezultate

```bash
python -m unittest discover -s tests -v
```

Toate cele **22 de teste locale** trec: 12 pentru laboratorul 2 și 10 pentru laboratorul 3. Noile verificări acoperă maparea ID-ului și a tipurilor, toate cele 49 de loturi, ultimul lot de 3, erorile individuale, răspunsurile incomplete, citirea mai multor pagini, valorile diferite, filmele lipsă, item-urile suplimentare și reluarea limitată a verificării.

Separat de testele cu API simulat, am confirmat prin API-ul real toate cele 4.803 filme și cele 33.621 de valori ale proprietăților pe 29 octombrie 2026.

Fișierele `.env`, mediul virtual și rapoartele locale sunt excluse din Git. Raportul nu conține tokenul privat. În modul `--verify-only`, `batches_sent` este 0 deoarece acea rulare doar citește catalogul.

## 8. Structura proiectului

```text
lab02-recombee-movies/
├── archive-3/
│   ├── tmdb_5000_movies.csv
│   └── tmdb_5000_credits.csv
├── tests/
│   ├── test_recombee_properties.py
│   └── test_recombee_items.py
├── recombee_properties.py
├── recombee_items.py
├── requirements.txt
├── .env.example
├── .gitignore
├── .gitattributes
└── README.md
```

## 9. Probleme care pot apărea

| Situație | Ce verific |
| --- | --- |
| `ModuleNotFoundError` | Activez mediul virtual și instalez `requirements.txt`. |
| Lipsesc variabile `RECOMBEE_...` | Completez configurația locală `.env`. |
| HTTP 401 / 403 | Verific tokenul privat, baza, regiunea și permisiunile. |
| Lipsește o proprietate / tip diferit | Verific schema de la laboratorul 2 înainte de import. |
| Un lot conține erori | Verific ID-urile indicate; pot relua importul după corectare. |
| Catalogul încă se actualizează | Aștept puțin și rulez `--verify-only`. |
| `NotOpenSSLWarning` pe macOS | Pot folosi Python 3.11+ cu OpenSSL și recrea mediul virtual. |

## Surse

- [Cerințele laboratorului 3](https://github.com/GG-Academy/Recommender-Systems/tree/main/lab03/ro)
- [Scriptul de pornire al laboratorului](https://github.com/GG-Academy/Recommender-Systems/blob/main/lab03/recombee_items.py)
- [Movies Dataset pe Kaggle](https://www.kaggle.com/datasets/akshaydattatraykhare/movies-dataset)
- [SDK-ul Python Recombee](https://docs.recombee.com/python_client)
- [API Recombee](https://docs.recombee.com/api)
- [Listarea item-urilor](https://docs.recombee.com/api/items)

Pagina Kaggle indică licența „Other (specified in description)”. Conform descrierii autorului, dataset-ul folosește API-ul TMDb și nu este aprobat sau certificat de TMDb.
