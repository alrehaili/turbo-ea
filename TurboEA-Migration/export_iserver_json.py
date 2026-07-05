#!/usr/bin/env python3
"""
iServer SQL Server -> UTF-8 JSON exporter
=========================================

Dumps the iServer tables needed by iserver_to_turboea.py to JSON, reading text
as proper Unicode so non-Latin names (Arabic, etc.) are NOT corrupted.

This is the fix for the "??????" (mojibake) problem: it reads NVARCHAR columns
via pyodbc and writes with ensure_ascii=False to a UTF-8 file.

PREREQUISITES
-------------
    pip install pyodbc
    Microsoft ODBC Driver 18 for SQL Server installed.
    The restored iServerDB reachable (e.g. the Docker container from the demo:
        Server=localhost,1433  User=SA  Db=iServerDB).

USAGE
-----
    python export_iserver_json.py \
        --server "localhost,1433" --db iServerDB --user SA --password "***" \
        --out "F:\\Iserver\\Exports"
"""

import argparse
import decimal
import json
import os
import sys
import datetime

# Tables consumed by the ETL. Add more if you extend the mapping.
TABLES = [
    "Object", "ObjectType", "Relation", "RelationType",
    "Attribute", "AttributeValue", "User",
]


def jsonable(v):
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (bytes, bytearray)):
        return None  # skip binary blobs (images, etc.)
    return v


def main():
    ap = argparse.ArgumentParser(description="Export iServer tables to UTF-8 JSON.")
    ap.add_argument("--server", required=True, help='e.g. "localhost,1433"')
    ap.add_argument("--db", default="iServerDB")
    ap.add_argument("--user", help="SQL login (omit when using --trusted)")
    ap.add_argument("--password", help="SQL password (omit when using --trusted)")
    ap.add_argument("--trusted", action="store_true",
                    help="Use Windows/AD authentication instead of a SQL login")
    ap.add_argument("--out", required=True, help="Output folder for *.json")
    ap.add_argument("--driver", default="ODBC Driver 18 for SQL Server")
    args = ap.parse_args()

    if not args.trusted and not (args.user and args.password):
        sys.exit("ERROR: provide --user and --password, or use --trusted for Windows auth")

    try:
        import pyodbc
    except ImportError:
        sys.exit("ERROR: pip install pyodbc  (and install the MS ODBC driver)")

    auth = ("Trusted_Connection=yes;" if args.trusted
            else f"UID={args.user};PWD={args.password};")
    # TrustServerCertificate is only valid for the modern "ODBC Driver 17/18";
    # the legacy "SQL Server" driver rejects it.
    extra = "TrustServerCertificate=yes;" if "ODBC Driver" in args.driver else ""
    conn_str = (
        f"DRIVER={{{args.driver}}};SERVER={args.server};DATABASE={args.db};"
        f"{auth}{extra}"
    )
    print(f"Connecting to {args.server}/{args.db} ...")
    cn = pyodbc.connect(conn_str)
    cn.setdecoding(pyodbc.SQL_CHAR, encoding="utf-8")
    cn.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-8")
    cur = cn.cursor()

    os.makedirs(args.out, exist_ok=True)
    for tbl in TABLES:
        try:
            cur.execute(f"SELECT * FROM [{tbl}]")
        except pyodbc.Error as e:
            print(f"  ! skip [{tbl}]: {e}")
            continue
        cols = [c[0] for c in cur.description]
        rows = [{c: jsonable(v) for c, v in zip(cols, r)} for r in cur.fetchall()]
        path = os.path.join(args.out, f"{tbl}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        print(f"  {tbl:16} {len(rows):>8} rows -> {path}")

    cn.close()
    print("Done. Next: python iserver_to_turboea.py")


if __name__ == "__main__":
    main()
