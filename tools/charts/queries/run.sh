#!/bin/bash

python3 query.py

python3 ../gen.py --out_dir=output/nl/jsons --include_url_in_result=True --min_to_skip=0 --in_pattern=output/nl/urls/shard_*.txt

python3 ../gen.py --out_dir=output/stat/jsons --include_url_in_result=True --min_to_skip=0 --in_pattern=output/stat/urls/shard_*.txt
