API Reference
=============

Data layer
----------

Loads and caches raw fault model data, exposing enriched subsections/ruptures tables that every
other layer builds on.

parserf.models
~~~~~~~~~~~~~~~

.. automodule:: parserf.models
   :members:
   :show-inheritance:

Spatial queries
----------------

Standalone functions that take a dataset and a coordinate: find the nearest subsection, list
nearby subsections/parents, or pull ruptures near a site.

parserf.queries
~~~~~~~~~~~~~~~~

.. automodule:: parserf.queries
   :members:
   :show-inheritance:

Subsection & parent views
---------------------------

Facades over a single fault subsection or parent fault, each exposing ``.data`` (attributes) and
``.ruptures`` (participation + MFDs).

parserf.subsection
~~~~~~~~~~~~~~~~~~~~

.. automodule:: parserf.subsection
   :members:
   :show-inheritance:

parserf.parent
~~~~~~~~~~~~~~~~

.. automodule:: parserf.parent
   :members:
   :show-inheritance:

Batch selection
-----------------

Batch access for downstream source-model building: many parent faults' subsections and ruptures
in one rupture-table scan, plus background gridded seismicity near a site.

parserf.selection
~~~~~~~~~~~~~~~~~~~~

.. automodule:: parserf.selection
   :members:
   :show-inheritance:
