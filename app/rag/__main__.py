from app.rag.service import ingest, stats

print(f"ingested {ingest()} chunks")
for source, count in stats().items():
    print(f"  {count:3d}  {source}")
