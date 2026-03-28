"""Parent fault view objects for earthquake rupture forecast datasets."""

from __future__ import annotations

from functools import cached_property

import pandas as pd

from parserf.models import FaultModel, FaultModelDataset
from parserf.utils import _cumulative_mfd


class ParentFaultData:
    """Dataset-backed view of a parent fault's subsection attributes.

    Args:
        dataset: The fault model dataset backing this view.
        parent_id: The parent fault integer ID.

    Attributes:
        fault_model: The fault model enum value.
        name: Parent fault name.
        parent_id: Integer ID of the parent fault.
        subsections: DataFrame of all child subsection attributes.
    """

    def __init__(self, dataset: FaultModelDataset, *, parent_id: int) -> None:
        self._dataset = dataset
        self._parent_id = parent_id
        pid_to_name = dataset.parent_ids.set_index("parent_id")["parent_name"]
        self._name = pid_to_name[parent_id]

    @property
    def fault_model(self) -> FaultModel:
        """The fault model enum value."""
        return self._dataset.model

    @property
    def name(self) -> str:
        """Parent fault name."""
        return self._name

    @property
    def parent_id(self) -> int:
        """Integer ID of the parent fault."""
        return self._parent_id

    @cached_property
    def subsections(self) -> pd.DataFrame:
        """DataFrame of all child subsection attributes.

        Columns include index, name, dip, dip_direction, upper_depth_km, lower_depth_km,
        aseismicity, length_km, width_km, area_km2, and geometry.
        """
        table = self._dataset._subsection_table
        df = table.loc[table["parent-id"] == self._parent_id].copy()
        df = df.rename(
            columns={
                "dip-direction": "dip_direction",
                "upper-depth": "upper_depth_km",
                "lower-depth": "lower_depth_km",
            }
        )
        columns = [
            "name",
            "dip",
            "dip_direction",
            "upper_depth_km",
            "lower_depth_km",
            "aseismicity",
            "length_km",
            "width_km",
            "area_km2",
            "geometry",
        ]
        return df[columns].rename_axis("index")

    @cached_property
    def style_counts(self) -> pd.DataFrame:
        """Faulting style breakdown by rupture count, sorted descending.

        Returns a DataFrame with columns ``style`` and ``count``.
        """
        rakes = self._dataset.rake_frequencies
        parent_rakes = rakes.loc[rakes["parent_id"] == self._parent_id]
        counts = parent_rakes.groupby("style")["count"].sum().reset_index()
        return counts.sort_values("count", ascending=False).reset_index(drop=True)

    @property
    def style(self) -> str:
        """The most common faulting style by rupture count."""
        return self.style_counts["style"].iloc[0]


class ParentFaultRuptures:
    """Dataset-backed view of rupture participation across a parent fault's subsections.

    Args:
        dataset: The fault model dataset backing this view.
        parent_id: The parent fault integer ID.
    """

    def __init__(self, dataset: FaultModelDataset, *, parent_id: int) -> None:
        self._dataset = dataset
        self._parent_id = parent_id

    @cached_property
    def _subsection_indices(self) -> list[int]:
        """Child subsection indices for this parent fault."""
        table = self._dataset._subsection_table
        return table.loc[table["parent-id"] == self._parent_id].index.tolist()

    @cached_property
    def cumulative_mfds(self) -> pd.DataFrame:
        """Cumulative magnitude frequency distributions for all child subsections.

        Returns a DataFrame with columns ``index`` (subsection index), ``magnitude``, and
        ``cumulative_rate``.
        """
        all_rups = self._dataset.ruptures_parsed
        frames = []
        for idx in self._subsection_indices:
            mask = all_rups["parsed_indices"].apply(lambda s, i=idx: i in s)
            filtered = all_rups.loc[mask]
            mfd = _cumulative_mfd(filtered)
            mfd.insert(0, "index", idx)
            frames.append(mfd)
        return pd.concat(frames, ignore_index=True)


class ParentFault:
    """Thin facade over a parent fault and its child subsections.

    Validates that the parent fault name exists in the dataset, then exposes ``.data`` for
    subsection attributes and ``.ruptures`` for rupture-query logic.

    Args:
        dataset: The fault model dataset backing this view.
        name: The parent fault name (e.g., "Airport Lake").

    Raises:
        ValueError: If the parent fault name is not found in the dataset.

    Examples:
        >>> from parserf.models import FaultModel, FaultModelDataset
        >>> from parserf.parent import ParentFault
        >>> ds = FaultModelDataset(FaultModel.UCERF3_31)
        >>> flt = ParentFault(ds, name="Airport Lake")
        >>> flt.data.name
        'Airport Lake'
        >>> flt.data.subsections
        ...
    """

    def __init__(self, dataset: FaultModelDataset, *, name: str) -> None:
        self._dataset = dataset
        self._name = name
        self._parent_id = dataset.get_parent_id(name=name)

    def __repr__(self) -> str:
        return (
            f"ParentFault(fault_model={self._dataset.model.name}, "
            f"name='{self._name}', parent_id={self._parent_id})"
        )

    @cached_property
    def data(self) -> ParentFaultData:
        """Parent fault attributes and child subsection data."""
        return ParentFaultData(self._dataset, parent_id=self._parent_id)

    @cached_property
    def ruptures(self) -> ParentFaultRuptures:
        """Rupture participation data across child subsections."""
        return ParentFaultRuptures(self._dataset, parent_id=self._parent_id)
