from pathlib import Path
import signal

from tqdm import tqdm
from slide.database import DataCollectionPolicy
from slide.database.models.base import BaseDTO
from slide.feature import FeatureExtractionEngine, FeatureExtractionPolicy
from slide.logger import Logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event

logging = Logger()
logger = logging.get_logger()


class FeatureEngine(FeatureExtractionEngine):
    def __init__(self, policy: FeatureExtractionPolicy, data_collection_policy: DataCollectionPolicy) -> None:
        self.data_collection_policy = data_collection_policy
        super().__init__(policy)
        # Setup signal handler for Ctrl+C
        self.stop_event = Event()
        signal.signal(signal.SIGINT, self.__signal_handler)

    def __signal_handler(self, signum, frame):
        logger.info("Received interrupt signal. Stopping gracefully...")
        self.stop_event.set()

    def process_item(self, d: BaseDTO) -> list | None:
        if self.stop_event.is_set():
            return None

        if not (Path(d.path) / d.name).exists():
            logger.warning(f"File {d.path}/{d.name} does not exist. Skipping.")
            return None

        features = self.policy.extract(d)
        if features:
            self.data_collection_policy.save(features)
        return features

    def collect(self) -> None:
        logger.info("Starting data collection for feature extraction.")
        data = self.data_collection_policy.collect()
        logger.info(f"Collected {len(data)} items for feature extraction.")

        if not data:
            logger.info("No data to process.")
            return

        # Use ThreadPoolExecutor for CPU-bound tasks
        max_workers = min(len(data), 5)  # Adjust based on your needs

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_item = {executor.submit(self.process_item, d): d for d in data}

                # Process completed tasks with progress bar
                with tqdm(total=len(data), desc="Extracting features", position=0, unit="file") as pbar:
                    for future in as_completed(future_to_item):
                        if self.stop_event.is_set():
                            logger.info("Cancelling remaining tasks...")
                            # Cancel remaining futures
                            for f in future_to_item:
                                f.cancel()
                            break

                        try:
                            result = future.result()
                            pbar.update(1)
                        except Exception as e:
                            item = future_to_item[future]
                            logger.error(f"Error processing {item}: {e}")
                            pbar.update(1)

        except KeyboardInterrupt:
            logger.error("Feature extraction interrupted by user.")
            self.stop_event.set()
            raise

        if self.stop_event.is_set():
            logger.info("Feature extraction stopped by user.")
        else:
            logger.info("Feature extraction completed successfully.")
