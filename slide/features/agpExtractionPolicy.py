from abc import ABC, abstractmethod
import re
from typing import Tuple
from slide.database.models.agp import AgpLithologyDTO, AgpSummaryDTO
from slide.database.models.download import DownloadDTO
from slide.features import PostProcessingPolicy


class AgpTableExtractor(PostProcessingPolicy, ABC):
    def __init__(self):
        self.well = None
        self.basin = None

    @property
    @abstractmethod
    def table(self) -> re.Pattern:
        pass

    @property
    @abstractmethod
    def rows(self) -> re.Pattern:
        pass

    @abstractmethod
    def build(self, row: Tuple):
        pass

    def ensure_well_and_basin(self) -> None:
        if self.well and self.basin:
            return
        with open(self.agp, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        reg = r"POCO\s*:\s*(?P<POCO>.+?)\s*\n.*?BACIA\s*:\s*(?P<BACIA>.+?)\s*\("
        match = re.search(reg, content[0:2000], re.DOTALL)
        self.well = match.group("POCO").strip().split("\n")[0].strip() if match else None
        self.basin = match.group("BACIA").strip().split("\n")[0].strip() if match else None

        if not self.well:
            reg = r"POO\s*:\s*(?P<POCO>.+?)\s*\n.*?BACIA\s*:\s*(?P<BACIA>.+?)\s*\("
            match = re.search(reg, content[0:2000], re.DOTALL)
            self.well = match.group("POCO").strip() if match else None

    def process(self, data: DownloadDTO) -> list:
        self.agp = f"{data.path}/{data.name}"
        self.well = None
        self.basin = None

        with open(self.agp, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # Find the LITOLOGIA table section
        match = re.search(self.table, content)
        if not match:
            return []
        table_text = match.group(1)
        # Improved regex: TOPO is optional, all columns after ROCHA are optional
        rows = re.findall(self.rows, table_text)
        data = [self.build(row) for row in rows]
        return data


class Summary(AgpTableExtractor):
    @property
    def table(self) -> re.Pattern:
        return re.compile(r"RESUMO DAS ROCHAS ENCONTRADAS NO POCO -\s*\n(.*?)(?:\n\s*\n|\Z)", re.DOTALL)

    @property
    def rows(self) -> re.Pattern:
        return re.compile(r"^\s*(\d+)\s+([A-Z .]+?)\s*=\s*([\d.]+)\s*M\s*([\d.]+)\s*%", re.MULTILINE)

    def build(self, row: Tuple) -> AgpSummaryDTO:
        self.ensure_well_and_basin()
        cod, rocha, metros, percentual = row
        return AgpSummaryDTO(
            well=self.well,
            basin=self.basin,
            code=cod,
            rock=rocha,
            meters=float(metros),
            percentage=float(percentual),
        )


class Lithology(AgpTableExtractor):
    @property
    def table(self) -> re.Pattern:
        return re.compile(
            r"LITOLOGIA -(?: \*\*\* VALORES VERTICALIZADOS \*\*\*)?\s*\n(?:-+\s*\n)?\s*(.*?)(?=\n\s*\n|$)", re.DOTALL
        )

    @property
    def rows(self) -> re.Pattern:
        return re.compile(
            r"^\s*(?:(?P<topo>[\d.]+)\s*\([^)]+\))?\s*"
            r"(?P<base>[\d.]+)\s*\([^)]+\)\s*"
            r"(?P<cod>\d+)\s+(?P<rocha>[A-Z]+)"
            r"(?:\s+(?P<cor>[A-Z]+))?"
            r"(?:\s+(?P<tonalidade>[A-Z]+))?"
            r"(?:\s+(?P<granulometria>[A-Z]+))?"
            r"(?:\s+(?P<arredondamento>[A-Z]+))?"
            r"\s*$",
            re.MULTILINE,
        )

    def build(self, row: Tuple) -> AgpLithologyDTO:
        self.ensure_well_and_basin()
        topo, base, cod, rocha, cor, tonalidade, granulometria, arredondamento = row
        return AgpLithologyDTO(
            basin=self.basin,
            well=self.well,
            id=cod,
            top=topo if topo else None,
            bottom=base if base else None,
            rock=rocha,
            color=cor,
            hue=tonalidade,
            granulometry=granulometria,
            roundness=arredondamento,
        )
