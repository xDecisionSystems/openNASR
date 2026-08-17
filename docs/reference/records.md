# FAA records and typed fields

`FaaRecord` is a lossless mapping: original FAA values remain available through
mapping access, `raw`, and `as_dict()`. Record subclasses add typed properties
without rewriting the source data. Conversion errors include table, column,
cycle, and record context when available.

```{eval-rst}
.. automodule:: openNASR.records
```
