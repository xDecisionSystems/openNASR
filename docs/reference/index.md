# Python API reference

The generated reference below documents openNASR's supporting table, record,
query, plotting, and error APIs directly from the installed package. The
{doc}`../types/index` provides one focused page for each major domain type.
Start with {doc}`../using-the-library` for setup, storage choices, usage
patterns, and identifier rules.

```{toctree}
:maxdepth: 2

core
records
query-storage
plotting-coordinates
exceptions
```

## How the object model fits together

`NASR` selects one exact FAA cycle and behaves as a lazy mapping of FAA table
names to pandas `DataFrame` objects. Its repository attributes turn those raw
tables into three useful layers:

1. **Repositories** provide normalized `get(...)` and `find(...)` lookups.
2. **Domain objects** group a primary record with ordered child records and
   resolved relationships.
3. **Records** retain every original FAA field while adding typed convenience
   properties for commonly used values.

The legacy `Airport`, `FIX`, and `NAVAID` constructors remain available for
compatibility and are documented on their corresponding type pages. New
applications should prefer the repository facade.
