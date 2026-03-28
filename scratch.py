# Note: this is just a scratch file for testing things out. It should be deleted eventually.


#TODO: thinking ahead to ParentFault, it will need:
# - coordinates (ordered so that dip is correct); how to deal with multilinestrings?

#

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from parserf.models import FaultModel, FaultModelDataset
from parserf.subsection import FaultSubsection, FaultSubsectionData, FaultSubsectionRuptures

def parent_pct_cdf(sub):
    """Return sorted pct values and cumulative probabilities for the subsection's parent fault."""
    parent = sub.data.parent_name
    pcts = sub.ruptures.participating_ruptures["parent_area_pcts"].apply(
        lambda d: d.get(parent, 0.0)
    ).values
    sorted_pcts = np.sort(pcts)
    cdf = np.arange(1, len(sorted_pcts) + 1) / len(sorted_pcts)
    return sorted_pcts, cdf

dataset = FaultModelDataset(FaultModel.NSHMP_2023)
idx = dataset.nearest_index(lat=32.877476, lon=-117.206703)

sub = FaultSubsection(dataset, index=idx)

print(sub.ruptures.cumulative_mfd.head())

# sorted_pcts, cdf = parent_pct_cdf(sub)
# print(cdf[-200:])
# print(sorted_pcts[-200:])
# fig, ax = plt.subplots(figsize=(7, 4))
# ax.plot(sorted_pcts, cdf, linewidth=1.5)
# ax.set_xlabel("Parent fault area participation (%)")
# ax.set_ylabel("Cumulative probability")
# ax.set_title(f"Parent fault participation CDF — {sub.data.name}")
# ax.set(xlim=(0, 100), ylim=(0, 1))
# plt.show()





# df1 = sub.ruptures.participating_ruptures
# df2 = sub.ruptures.cumulative_mfd
# df1.to_csv("participating_ruptures.csv", index=False)
# df2.to_csv("cumulative_mfd.csv", index=False)

# print(vars(sub.data))
# print("sub.data.name:", sub.data.name)
# print("sub.data.length_km:", sub.data.length_km)
# print("/n/n")

# print(vars(sub.ruptures))
# print("sub.ruptures.participating_ruptures.head():", sub.ruptures.participating_ruptures.head())
# print("sub.ruptures.participating_ruptures.tail():", sub.ruptures.participating_ruptures.tail())
# print("sub.ruptures.participating_ruptures.columns:", sub.ruptures.participating_ruptures.columns)
# print("/n/n")

# sub2=FaultSubsectionData(dataset, index=0)
# print(vars(sub2))

# sub3=FaultSubsectionRuptures(dataset, index=0)
# print(vars(sub3))
