# Utility to build a ton of charts

## Set-up

To generate `var_existence.csv`, run:

```
SELECT DISTINCT O.observation_about AS Place, V.dcid AS Var
FROM `datcom-store.scratch.ChartVars` AS V
JOIN `datcom-store.scratch.ChartPlaces` AS P ON TRUE
JOIN `datcom-store.scratch.StatVarObservation` AS O ON TRUE
WHERE
   O.variable_measured = V.dcid AND
   O.observation_about = P.dcid
ORDER BY Place, Var;
```

Where, ChartVars and ChartPlaces are tables representing CSVs
`all_vars.csv` and `all_places.csv`.

## Run

```bash
python3 places.py
python3 urls.py
python3 gen.py
```