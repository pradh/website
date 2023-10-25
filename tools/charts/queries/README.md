# Utility to extract a bunch of Chart Server responses

## Set-up

To generate `query_var_existence.csv`, run:

```
SELECT DISTINCT O.observation_about AS Place,
                V.dcid AS Var,
                PL.name AS PlaceName,
                SV.name AS VarName
FROM `datcom-store.scratch.QueryChartVars` AS V
JOIN `datcom-store.scratch.ChartPlaces` AS P ON TRUE
JOIN `datcom-store.dc_kg_latest.StatVarObservation` AS O ON TRUE
JOIN `datcom-store.dc_kg_latest.Place` AS PL ON TRUE
JOIN `datcom-store.dc_kg_latest.StatisticalVariable` AS SV ON TRUE
WHERE
   O.variable_measured = V.dcid AND
   O.observation_about = P.dcid AND
   P.dcid = PL.id AND
   V.dcid = SV.id
ORDER BY Place, Var;
```

Where, QueryChartVars and ChartPlaces are tables representing CSVs
`query_vars.csv` and `../all_places.csv`.

## Run

```bash
python3 query_urls.py
python3 ../gen.py
```
