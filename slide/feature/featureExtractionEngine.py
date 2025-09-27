

from pathlib import Path

from tqdm import tqdm
from slide.database import BaseDAO, DataCollectionPolicy
from slide.feature import FeatureExtractionEngine, FeatureExtractionPolicy
from slide.logger import Logger

logging = Logger()
logger = logging.get_logger()

class FeatureEngine(FeatureExtractionEngine):

    def __init__(self, policy: FeatureExtractionPolicy, data_collection_policy: DataCollectionPolicy, dao: BaseDAO) -> None:
        self.dao = dao
        self.data_collection_policy = data_collection_policy
        super().__init__(policy)
    
    def collect(self) -> list:

        logger.info("Starting data collection for feature extraction.")
        data = self.data_collection_policy.collect()
        logger.info(f"Collected {len(data)} items for feature extraction.")

        features: list = [
            f
            for d in tqdm(data)
            if (Path(d.path) / d.name).exists()
            for f in self.policy.extract(d)
        ]

        logger.info(f"Extracted {len(features)} features.")

        self.dao.bulk_insert(features)
        return features