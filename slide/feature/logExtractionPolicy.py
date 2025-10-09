from abc import abstractmethod
from slide.database.models.download import LogDownloadDTO
from slide.database.models.log import LogChannelsDTO, LogDTO
from slide.feature import FeatureExtractionPolicy
from dlisio import dlis
from dlisio.dlis import LogicalFile, Channel
from slide.logger import Logger
from tqdm import tqdm

logging = Logger()
logger = logging.get_logger()



class LogExtractionPolicy(FeatureExtractionPolicy):

    def __init__(self) -> None:
        pass

    def extract(self, log: LogDownloadDTO) -> list[dict]:

        file_name = f"{log.path}/{log.name}"
        valid_channels = ['CALI', 'SP', 'GR', 'DT', 'ILD', 'RHOB', 'NPHI', 'DRHO', 'MSFL', 'SFLU']

        try: 
            with dlis.load(f"{file_name}") as dlis_file:

                records: dict[float, dict[str, float]] = {}

                for logical_file in dlis_file:
                    
                    file: LogicalFile = logical_file
                    index_channel: Channel = next(c for c in file.channels if "INDEX" in c.name.upper())
                    channels: list[Channel] = [
                        c for c in file.channels 
                        if c.name.upper() in valid_channels
                    ]
                    
                    index_curves = index_channel.curves()
                    
                    channels_curves: dict[str, list[float]] = {channel.name: channel.curves() for channel in channels}

                    for i in tqdm(range(0, len(index_curves) - 1), desc=f"Processing file {file}", leave=False, miniters=1):
                        depth = index_curves[i]

                        for channel_name, curves in channels_curves.items():
                            depth_record = records.get(depth, {})

                            if i >= len(curves):
                                #logger.warning(f"Channel {channel_name} has no value at index {i} (depth {depth}) in file {file}. Skipping.")
                                continue

                            depth_record[channel_name.upper()] = curves[i]
                            
                            records[depth] = depth_record
        
        
        
        except Exception as e:
            logger.error(f"Error processing DLIS file {file_name}: {e}")
            return []
          
        data_points = self.__post_processing(records)
        data_points = [
            LogDTO(
                well=log.well,
                depth=depth,
                CALI=depth_record.get("CALI", None),
                SP=depth_record.get("SP", None),
                GR=depth_record.get("GR", None),
                DT=depth_record.get("DT", None),
                ILD=depth_record.get("ILD", None),
                RHOB=depth_record.get("RHOB", None),
                NPHI=depth_record.get("NPHI", None),
                DRHO=depth_record.get("DRHO", None),
                MSFL=depth_record.get("MSFL", None),
                SFLU=depth_record.get("SFLU", None)
            )
            for depth, depth_record in records.items()
        ]

        logger.debug(f"Extracted {len(data_points)} log data points from file {file_name}.")

        return data_points
    
class LogChannelsExtractionPolicy(FeatureExtractionPolicy):

    def __init__(self) -> None:
        pass

    def extract(self, log: LogDownloadDTO) -> list[dict]:

        file_name = f"{log.path}/{log.name}"
        try: 
            with dlis.load(f"{file_name}") as dlis_file:
                records: dict[str, int] = {}

                for logical_file in dlis_file:
                    
                    file: LogicalFile = logical_file
                    channels: list[Channel] = [
                        c for c in file.channels 
                        if not any(keyword in c.name.upper() for keyword in ["INDEX", "DUMM", "_"])
                    ]

                    for channel in channels:
                        records[channel.name] = len(channel.curves())
                
                data_points = [
                    LogChannelsDTO(
                        well=log.well,
                        channel=channel_name,
                        total_data=total_data
                    )
                    for channel_name, total_data in records.items()
                ]

                logger.debug(f"Extracted {len(data_points)} log data points from file {file_name}.")
        except Exception as e:
            logger.error(f"Error processing DLIS file {file_name}: {e}")
            return []
        return data_points