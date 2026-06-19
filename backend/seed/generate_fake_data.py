import asyncio
import logging
import argparse
from seed.factory import set_seed
from seed.seed_database import seed_all

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Seed the AskDB Database with fake realistic enterprise data.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for repeatability")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear existing data before seeding")
    args = parser.parse_args()

    set_seed(args.seed)
    
    logger.info("Starting database seeding process...")
    await seed_all(clear=not args.no_clear)

if __name__ == "__main__":
    asyncio.run(main())
