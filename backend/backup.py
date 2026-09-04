import argparse, json, zipfile
from pathlib import Path
from .db import engine, Base, transaction

def main():
    parser=argparse.ArgumentParser(description='Backup completo do Livro-Ponto')
    parser.add_argument('destination')
    args=parser.parse_args()
    target=Path(args.destination)
    target.parent.mkdir(parents=True,exist_ok=True)
    with transaction() as db, zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for table in Base.metadata.sorted_tables:
            rows=[dict(r) for r in db.execute(table.select()).mappings()]
            archive.writestr(table.name+'.json',json.dumps(rows,ensure_ascii=False,default=str))
    print('Backup salvo em',target.resolve())
if __name__=='__main__': main()
