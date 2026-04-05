"""Parent fault selection for batch earthquake rupture forecast queries."""

from __future__ import annotations

from functools import cached_property

import geopandas as gpd
import pandas as pd

from parserf._utils import _parent_style, _parent_surface_trace, _RuptureSet
from parserf.models import FaultModelDataset


class ParentSelection:
    """Scoped view of a dataset for a set of parent faults.

    Provides efficient batch access to subsection attributes, parent summaries, and enriched
    rupture data for all subsections belonging to the selected parents.

    Args:
        dataset: The fault model dataset backing this view.
        parent_ids: Ordered list of parent fault IDs to include.

    Raises:
        ValueError: If any parent fault ID is not found in the dataset.

    Examples:
        >>> from parserf.models import FaultModel, FaultModelDataset
        >>> from parserf.queries import get_parents_list
        >>> from parserf.selection import ParentSelection
        >>> ds = FaultModelDataset(FaultModel.UCERF3_31)
        >>> pids = get_parents_list(ds, lat=35.77, lon=-117.60, dist_km=150)
        >>> sel = ParentSelection(ds, pids)
        >>> sel.parents
        ...
        >>> sel.ruptures
        ...
    """

    def __init__(self, dataset: FaultModelDataset, parent_ids: list[int]) -> None:
        if not parent_ids:
            raise ValueError("parent_ids must not be empty")
        for pid in parent_ids:
            dataset._validate_parent_id(pid)
        self._dataset = dataset
        self._parent_ids = list(parent_ids)

    @property
    def parent_ids(self) -> list[int]:
        """Input parent fault IDs in their original order."""
        return self._parent_ids

    @cached_property
    def subsections(self) -> pd.DataFrame:
        """All subsections for the selected parents (full extent).

        Returns the subset of ``dataset.subsections`` whose ``parent_id`` is in the selection,
        preserving the original index and columns.
        """
        subs = self._dataset.subsections
        return subs.loc[subs["parent_id"].isin(self._parent_ids)]

    @cached_property
    def parents(self) -> gpd.GeoDataFrame:
        """Per-parent summary with faulting style and oriented surface trace.

        Returns a GeoDataFrame indexed by ``parent_id`` (in input order) with columns
        ``parent_name``, ``style``, and ``geometry`` (oriented surface trace as LineString,
        EPSG:4326).
        """
        subs = self.subsections
        rakes = self._dataset.rake_frequencies

        records = []
        for pid, group in subs.groupby("parent_id"):
            weights = group["area_km2"]
            dip = (group["dip"] * weights).sum() / weights.sum()
            dip_dir = (group["dip_direction"] * weights).sum() / weights.sum()
            style = _parent_style(rakes, pid)
            trace = _parent_surface_trace(group["geometry"].tolist(), dip, dip_dir)
            records.append(
                {
                    "parent_id": pid,
                    "parent_name": group["parent_name"].iloc[0],
                    "style": style,
                    "geometry": trace,
                }
            )

        gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
        return gdf.set_index("parent_id").loc[self._parent_ids]

    @cached_property
    def _rupture_set(self) -> _RuptureSet:
        """Single rupture set for all subsections of selected parents."""
        return _RuptureSet(self._dataset, frozenset(self.subsections.index))

    @cached_property
    def ruptures(self) -> gpd.GeoDataFrame:
        """Enriched ruptures for all subsections of the selected parents.

        Returns a GeoDataFrame (EPSG:4326) in exploded form: one row per (rupture, parent) pair.
        The DataFrame index identifies the original rupture (duplicate index values indicate rows
        from the same rupture). Columns include ``m``, ``rate``, ``geometry``, ``length_km``,
        ``area_km2``, ``parent_id``, and ``area_pct``.

        The ``rate`` column is the full rupture rate; multiply by ``area_pct / 100`` to get the
        parent-attributed rate.

        All parent contributions for each rupture are included, not just parents in the selection.
        This preserves interpretable ``area_pct`` values that sum to 100 per rupture. Filter on
        ``parent_id`` to isolate specific parents.
        """
        return self._rupture_set.participating_ruptures
