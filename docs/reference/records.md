# FAA records and typed fields

`FaaRecord` is a lossless mapping: original FAA values remain available through
mapping access, `raw`, and `as_dict()`. Record subclasses add typed properties
without rewriting the source data. Conversion errors include table, column,
cycle, and record context when available.

## Base record and conversion context

```{eval-rst}
.. autoclass:: openNASR.records.FaaRecord
.. autoclass:: openNASR.records.FieldContext
```

## Typed conversion functions

```{eval-rst}
.. autofunction:: openNASR.records.boolean
.. autofunction:: openNASR.records.coordinate
.. autofunction:: openNASR.records.decimal
.. autofunction:: openNASR.records.enum_value
.. autofunction:: openNASR.records.float_value
.. autofunction:: openNASR.records.integer
.. autofunction:: openNASR.records.iso_date
.. autofunction:: openNASR.records.nullable_text
```
