"""M1 data pipeline: NUSMods prerequisite / preclusion parsing.

Public entry points:
    python -m m1_data fetch   # download raw NUSMods JSON (needs internet)
    python -m m1_data build   # raw JSON -> data/processed/<AY>/...
    python -m m1_data check   # validate processed data

    from m1_data.catalog import Catalog   # load processed data in Python
"""

__version__ = "1.0.0"
SCHEMA_VERSION = "1.0"
