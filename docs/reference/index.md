# Python API reference

The generated reference below documents openNASR's public classes, data
objects, methods, properties, and functions directly from the installed
package. Start with {doc}`../API` for usage patterns and identifier rules.

```{toctree}
:maxdepth: 2

core
facilities
airspace
routes
services
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

The legacy `Airport`, `FIX`, `NAVAID`, and `ARB` constructors remain available
for compatibility. New applications should prefer the repository facade.
