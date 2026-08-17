# Route regression fixtures

This directory is reserved for the small, tracked route sample used by the
route-path plan's T0.3 regression tests.  It is deliberately independent of
`tests/exampleRoutes.csv`, which is local-only data and is not part of the
repository.

## File format

`routes.json` is a UTF-8 JSON document with this shape:

```json
{
  "cycle_date": "YYYY-MM-DD",
  "routes": [
    {
      "id": "stable-name",
      "route": "ORIGIN ... DEST",
      "category": "category-from-T0.2"
    }
  ]
}
```

`cycle_date` pins every route to the NASR cycle used to classify it.  Each
route gets a stable ID so tests can report a failing case without relying on a
row number in an external file.  The category values must be the exact T0.2
classification (for example, `parser_error` or `missing_nasr_data`); route
strings must be copied verbatim from the classified sample.

The scaffold currently contains no route records.  T0.2 supplies the
classified representatives before T0.3 tests consume this file.
