from slide.database.models.download import LogDownloadDTO
from slide.database.models.log import LogDTO
from slide.feature import FeatureExtractionPolicy
from dlisio import dlis
from dlisio.dlis import LogicalFile, Channel



class LogExtractionPolicy(FeatureExtractionPolicy):

    def __init__(self) -> None:
        pass

    def extract(self, log: LogDownloadDTO) -> list[LogDTO]:

        dlis_file = dlis.load(f"{log.path}/{log.name}")

        records: list[LogDTO] = []

        for logical_file in dlis_file:
            
            file: LogicalFile = logical_file
            channels: list[Channel] = file.channels
            index_channel = channels.pop(-1)

            for i in range(0, len(index_channel)):
                record: dict = {
                    "well": log.well,
                    "depth": index_channel[i]
                }

                for channel in channels:
                    record[channel.name.upper()] = channel[i]
                
                records.append(LogDTO.model_validate(record))

        return records