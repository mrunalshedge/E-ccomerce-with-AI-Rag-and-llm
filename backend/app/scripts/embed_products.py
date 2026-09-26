"""(Re)compute product embeddings for semantic search.

Usage (from the project root):  npm run embed            # only products missing an embedding
                                npm run embed -- --all   # recompute every product
"""

import argparse
import asyncio

from app.db.session import SessionLocal, engine
from app.services.embedding_service import backfill_embeddings


async def main(recompute: bool) -> None:
    async with SessionLocal() as db:
        count = await backfill_embeddings(db, recompute=recompute)
    await engine.dispose()
    print(f"Embedded {count} products.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="recompute embeddings for every product")
    asyncio.run(main(parser.parse_args().all))
