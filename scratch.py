# Note: this is just a scratch file for testing things out. It should be deleted eventually.

# TODO: tests take a while to run
# TODO: FaultSubsectionRuptures needs a cumul_mfd property


#TODO: thinking ahead to ParentFault, it will need:
# - coordinates (ordered so that dip is correct); how to deal with multilinestrings?
# - some kind of list of the subsection indices and attributes (e.g., dip, width, etc. for each
#   subsection within the parent fault)
# - cumul mfds for all subsections (columns index, mag, cumul_rate)
#

import pandas as pd

from parserf.models import FaultModel, FaultModelDataset
from parserf.subsection import FaultSubsection, FaultSubsectionData, FaultSubsectionRuptures

dataset = FaultModelDataset(FaultModel.UCERF3_31)

sub = FaultSubsection(dataset, index=1126)
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
