#!/bin/bash

python3 rule_sampler.py -d icews14_tiny -m 2 -n 3 -p 1 -s 1 --is_relax_time No
python3 Iteration_reasoning.py -d icews14_tiny --model_name gpt-4o-mini -f 2 -l 1 --is_rel_name Yes
python3 rank_rule.py -p copy_gpt-4o-mini-top-0-f-2-l-1 -d icews14_tiny
python3 reasoning.py -p copy_gpt-4o-mini-top-0-f-2-l-1 -d icews14_tiny
python3 evaluate.py -d icews14_tiny -c 'llm_test_apply_all_conf_cands_r[1,2,3]_w0_score_12[0.1,0.5,\'TLogic\',0.0,0.01,0]_top_20_et_origin.json' --graph_reasoning_type TiRGN --rule_weight 0.9
