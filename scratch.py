# Note: this is just a scratch file for testing things out. It should be deleted eventually.

# TODO: can I have a git centric TODO list?

# TODO: tests take a while to run
# TODO:

# TODO: faultubsection needs to add length, width, area to the participating ruptures dataframe,
# so that we can easily access those values for each rupture.
# This will be useful for calculating the slip rate for each rupture,
# which is needed for the slip rate model.  ha not really but close, good try ai


from parserf.models import FaultModel, FaultModelDataset

dataset = FaultModelDataset(FaultModel.UCERF3_31)

# sub = FaultSubsection(dataset, index=0)
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
