from parserf.models import FaultModel, FaultModelDataset
from parserf.subsection import FaultSubsection

dataset = FaultModelDataset(FaultModel.UCERF3_31)
# parent_ids = dataset.parent_ids
# sections = dataset.sections
# ruptures = dataset.ruptures_parsed

# print(parent_ids)
# print(sections.head())
# print(ruptures.head())


sub = FaultSubsection(dataset, index=0)
print(sub.name)
print(sub.parent_id)
print(sub.parent_name)
print(sub.upper_depth)
print(sub.length_km)
print(sub.width_km)
print(sub.area_km2)
print(sub.participating_ruptures.head())
print(sub.participating_ruptures.tail())
