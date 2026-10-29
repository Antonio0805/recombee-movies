"""Laborator 3: importul filmelor în Recombee, în loturi de 100."""

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from recombee_api_client.api_client import RecombeeClient
from recombee_api_client.api_requests import Batch, ListItemProperties, ListItems, SetItemValues
from recombee_api_client.exceptions import APIException
from requests.exceptions import RequestException

# Refolosesc schema, validarea CSV-ului și configurația din laboratorul 2.
from recombee_properties import (
    PATH_DATASET, PROPRIETATI_CATALOG, REGIONS, ROOT,
    check_property_types, get_config, load_dataset,
)

BATCH_SIZE = 100
REPORT_PATH = ROOT / "reports" / "recombee_items.json"


class CatalogNotReady(ValueError):
    """Catalogul se poate actualiza încă după terminarea importului."""


def prepare_items(df):
    """id devine itemId; valorile sunt convertite la tipuri Python native."""
    converters = {"string": str, "int": int, "double": float}
    return [
        {
            "itemId": str(row["id"]),
            "values": {
                prop["name"]: converters[prop["type"]](row[prop["name"]])
                for prop in PROPRIETATI_CATALOG
            },
        }
        for row in df.to_dict(orient="records")
    ]


def send_items(client, items):
    """SetItemValues actualizează aceleași ID-uri la o reluare a importului."""
    batches = 0
    for start in range(0, len(items), BATCH_SIZE):
        chunk = items[start:start + BATCH_SIZE]
        requests = [SetItemValues(item["itemId"], item["values"], cascade_create=True)
                    for item in chunk]
        response = client.send(Batch(requests))
        # Un Batch HTTP 200 poate conține cereri individuale eșuate.
        if not isinstance(response, list) or len(response) != len(chunk):
            raise ValueError("Răspuns Batch incomplet. Importul poate fi reluat cu aceeași comandă.")
        failures = []
        for item, result in zip(chunk, response):
            code = result.get("code") if isinstance(result, dict) else None
            if not isinstance(code, int) or not 200 <= code < 300:
                failures.append(item["itemId"])
        if failures:
            raise ValueError(
                f"Lotul {batches + 1}: {len(failures)} cereri au eșuat; "
                f"ID-uri: {', '.join(failures[:10])}. Corectează problema și reia importul."
            )
        batches += 1
        print(f"Lot {batches}: {len(chunk)} filme confirmate; "
              f"progres {start + len(chunk)}/{len(items)}.", flush=True)
    return batches


def verify_items(client, items):
    """Citește catalogul paginat și compară TOATE valorile așteptate cu CSV-ul."""
    expected = {item["itemId"]: item["values"] for item in items}
    seen = set()
    total = 0
    offset = 0
    names = [prop["name"] for prop in PROPRIETATI_CATALOG]
    while True:
        page = client.send(ListItems(count=1000, offset=offset,
                                     return_properties=True, included_properties=names))
        if not isinstance(page, list):
            raise ValueError("Răspuns ListItems invalid.")
        if not page:
            break
        for remote in page:
            item_id = remote["itemId"]
            total += 1
            if item_id not in expected:
                continue
            if item_id in seen:
                raise CatalogNotReady("Catalogul s-a schimbat în timpul verificării; reia --verify-only.")
            seen.add(item_id)
            for name, value in expected[item_id].items():
                actual = remote.get(name)
                if isinstance(value, float):
                    matches = (isinstance(actual, (int, float)) and not isinstance(actual, bool)
                               and math.isfinite(actual)
                               and math.isclose(actual, value, rel_tol=1e-9, abs_tol=1e-9))
                else:
                    matches = type(actual) is type(value) and actual == value
                if not matches:
                    raise ValueError(f"Valoare diferită în Recombee: itemId={item_id}, proprietate={name}.")
        offset += len(page)
        # Continuăm până la pagina goală, inclusiv dacă API-ul limitează mărimea paginii.
    missing = set(expected) - seen
    if missing:
        raise CatalogNotReady(f"Lipsesc {len(missing)} filme din Recombee. Rulează importul.")
    print(f"Verificare API reușită: {len(seen)} filme, toate cele 7 proprietăți coincid cu CSV-ul.")
    return {"verified_items": len(seen), "catalog_items": total,
            "extra_items": total - len(seen), "verified_properties_per_item": len(names)}


def verify_with_retry(client, items):
    """Reia citirea dacă paginile încă reflectă actualizarea catalogului."""
    for attempt in range(3):
        try:
            return verify_items(client, items)
        except CatalogNotReady:
            if attempt == 2:
                raise
            print("Catalogul încă se actualizează; reiau verificarea în 2 secunde.", flush=True)
            time.sleep(2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=PATH_DATASET)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validare locală, fără API sau token")
    mode.add_argument("--verify-only", action="store_true", help="Compară catalogul cu CSV-ul, fără scriere")
    args = parser.parse_args(argv)
    try:
        df = load_dataset(args.dataset)
        items = prepare_items(df)
        print(f"Mapare: id → itemId. Plan: {math.ceil(len(items) / BATCH_SIZE)} loturi, maxim 100 filme/lot.")
        print("Exemplu de item:")
        print(json.dumps(items[0], ensure_ascii=False, indent=2))
        if args.dry_run:
            print("DRY RUN: date validate și convertite; nu s-a apelat Recombee.")
            return 0
        config = get_config()
        client = RecombeeClient(config["RECOMBEE_DATABASE_ID"], config["RECOMBEE_PRIVATE_TOKEN"],
                                region=REGIONS[config["RECOMBEE_REGION"]])
        check_property_types(client.send(ListItemProperties()), require_all=True)
        # Raportul este al acestei încercări; un eșec nu trebuie să lase un succes vechi.
        REPORT_PATH.parent.mkdir(exist_ok=True)
        report = {"status": "started", "started_at_utc": datetime.now(timezone.utc).isoformat(),
                  "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                  "dataset_rows": len(items), "mode": "verify-only" if args.verify_only else "import",
                  "batch_size": BATCH_SIZE}
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        batches = 0 if args.verify_only else send_items(client, items)
        verification = verify_with_retry(client, items)
        report.update(verification)
        report.update(status="success", batches_sent=batches,
                      verified_at_utc=datetime.now(timezone.utc).isoformat())
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Raport salvat: {REPORT_PATH.relative_to(ROOT)}")
        return 0
    except APIException as error:
        print(f"Eroare Recombee HTTP {getattr(error, 'status_code', 'necunoscut')}. "
              "Verifică autentificarea, regiunea și permisiunile. Importul poate fi reluat.", file=sys.stderr)
    except RequestException:
        print("Conexiunea la Recombee a eșuat. Reia comanda după restabilirea rețelei.", file=sys.stderr)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        print(f"Eroare: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
