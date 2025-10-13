from dataclasses import dataclass
from typing import Any


@dataclass
class ColumnDef:
    name: str
    dtype: str


@dataclass
class TableDef:
    name: str
    columns: list[ColumnDef]

    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "columns": [c.__dict__ for c in self.columns]}
