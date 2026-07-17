"""
MongoDB caching service for static provider and customer metadata.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config.settings import Settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProviderCache:
    """
    Handles MongoDB storage and lookup for static document fields.

    Static fields include provider information (name, address, timings, website, etc.)
    and customer information (name, id, address, service address, account type).
    Uses provider_name + account_number as the unique cache key.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._db = None
        self._collection = None

    def _get_collection(self):
        """Lazy-initialize MongoDB connection and create indices."""
        if self._collection is None:
            try:
                logger.info("Initializing MongoDB cache connection...")
                self._client = MongoClient(self.settings.MONGO_URI)
                self._db = self._client["bill_extraction"]
                self._collection = self._db["provider_cache"]
                # Create compound unique index
                self._collection.create_index(
                    [("provider_name", 1), ("account_number", 1)],
                    unique=True,
                )
                logger.info("MongoDB cache collection and index initialized")
            except Exception as e:
                logger.error("Failed to connect to MongoDB: %s", e)
                # Keep collection as None to prevent crashes; falls back to cache miss
                self._collection = None
        return self._collection

    def get(self, provider_name: str, account_number: str) -> Optional[Dict[str, Any]]:
        """
        Lookup static fields in the cache using provider name and account number.

        Args:
            provider_name: Name of the water provider.
            account_number: Customer's account number.

        Returns:
            Cached static details dict, or None if not found or on error.
        """
        if not provider_name or not account_number:
            return None

        # Clean strings for lookup consistency
        p_name = provider_name.strip().lower()
        acct_num = account_number.strip().lower()

        collection = self._get_collection()
        if collection is None:
            logger.warning("MongoDB cache unavailable, skipping lookup")
            return None

        try:
            # Case insensitive exact match using regex if stored as mixed case,
            # but we can query by raw values or do regex lookups.
            # Storing them standardized is best.
            query = {
                "provider_name_key": p_name,
                "account_number_key": acct_num,
            }
            logger.info("Looking up cache for key: %s | %s", p_name, acct_num)
            cached = collection.find_one(query)
            if cached:
                logger.info("Cache hit for: %s | %s", p_name, acct_num)
                return cached.get("static_data")
            else:
                logger.info("Cache miss for: %s | %s", p_name, acct_num)
        except PyMongoError as e:
            logger.error("MongoDB query error: %s", e)
        except Exception as e:
            logger.error("Unexpected cache lookup error: %s", e)

        return None

    def set(self, provider_name: str, account_number: str, static_data: Dict[str, Any]) -> bool:
        """
        Store static provider and customer metadata in the cache.

        Args:
            provider_name: Name of the water provider.
            account_number: Customer's account number.
            static_data: Dictionary of static fields.

        Returns:
            True if cached successfully, False otherwise.
        """
        if not provider_name or not account_number or not static_data:
            return False

        p_name = provider_name.strip().lower()
        acct_num = account_number.strip().lower()

        collection = self._get_collection()
        if collection is None:
            logger.warning("MongoDB cache unavailable, skipping write")
            return False

        try:
            query = {
                "provider_name_key": p_name,
                "account_number_key": acct_num,
            }
            update_doc = {
                "provider_name_key": p_name,
                "account_number_key": acct_num,
                "provider_name": provider_name.strip(),
                "account_number": account_number.strip(),
                "static_data": static_data,
                "last_updated": datetime.now(timezone.utc),
            }
            collection.replace_one(query, update_doc, upsert=True)
            logger.info("Cache updated for: %s | %s", p_name, acct_num)
            return True
        except PyMongoError as e:
            logger.error("Failed to write to MongoDB cache: %s", e)
        except Exception as e:
            logger.error("Unexpected cache write error: %s", e)

        return False

    def close(self):
        """Close MongoClient connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB client connection closed")
            self._client = None
            self._collection = None
