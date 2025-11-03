from pathlib import Path
import sqlite3

from slide.database.dataCollectionPolicy import DataCollectionPolicy, DataCollectionPolicy

from slide.logger import Logger

logging = Logger()
logger = logging.get_logger()


class FeatureCollectionPolicy(DataCollectionPolicy):
    def __init__(self, db_path: Path | str, *args, **kwargs):
        super().__init__(db_path, *args, **kwargs)
        
    def collect(self) -> list:
        db_path = Path(__file__).parent.parent.parent / "features.db"

        conn = sqlite3.connect(db_path)
        conn.enable_load_extension(True)
        conn.load_extension("regex0.dll")

        query = """
        DROP TABLE IF EXISTS agp_intervals;
        CREATE TABLE IF NOT EXISTS agp_intervals AS
        WITH agp_clean AS (
        SELECT
                replace(
                    regex_replace(
                        '([A-Za-z]*|^0[0-9])0+([A-Za-z0-9])',
                        a.well,'$1$2'),
                    " ", "") AS well_norm,
            a.top, a.bottom, a.rock
            FROM AGPLithology a
            WHERE a.well IS NOT NULL
        )
        SELECT
            well_norm AS well,
            COALESCE(top, LAG(bottom) OVER (PARTITION BY well_norm ORDER BY bottom)) AS top_filled,
            bottom,
            rock
        FROM agp_clean;

        CREATE INDEX IF NOT EXISTS lithology_well_intervals
            ON agp_intervals (well, bottom);

        CREATE INDEX IF NOT EXISTS logs_well_depth_btree
        ON LogsFeatures (well, depth);
        """

        conn.executescript(query)
        conn.commit()


        features = """
        DROP TABLE IF EXISTS Features;
        CREATE TABLE IF NOT EXISTS Features AS
        SELECT
            fl.well AS well,
            fl.depth,
            fl.GR,
            fl.SP,
            fl.DT,
            fl.CALI,
            fl.ILD,
            fl.RHOB,
            fl.NPHI,
            fl.MSFL,
            fl.DRHO,
            fl.SFLU,
            fa.top_filled AS top,
            fa.bottom,
            fa.rock
        FROM LogsFeatures fl
        LEFT JOIN agp_intervals fa
        ON fl.well = fa.well
            AND fl.depth > coalesce(fa.top_filled, bottom)
            AND fl.depth <= fa.bottom;

        CREATE INDEX IF NOT EXISTS features_logs_depth_btree
        ON Features (well, depth);
        """
        conn.executescript(features)
        conn.commit()
        
        return []
        
    def save(self, records: list) -> None:
        raise NotImplementedError("FeatureCollectionPolicy does not implement save method.")
        