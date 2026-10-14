# Goals from GeoAI-skills' evaluation tasks

`geoai_skills_small.txt` holds four of the tasks of [GeoAI-skills](https://github.com/yuiseki/GeoAI-skills) at commit
6926f3e, one Goal per line for `bench/run_explore.py --replay`, in this order:

| Line | GeoAI-skills task | Data the sandbox reads |
|---|---|---|
| 1 | small task 15 (`evals/tasks/small-tasks-fixed.md`): neighbouring municipalities | jp-admin |
| 2 | small task 14 (`evals/tasks/small-tasks.md`): population density by country, the data not named | WDI, Natural Earth |
| 3 | small task 17 (`evals/tasks/small-tasks-fixed.md`): the same, the data named and WDI's density not used | WDI, Natural Earth |
| 4 | task 11 (`evals/tasks/tasks.md`): the share of people within 1 km of a station | jp-admin, ekidata, WorldPop |

The wording is GeoAI-skills', put on one line each. Tasks 13 and 16 (the buildings of Taito) are left out: they read
osm-japan-src, whose tables are 6.5 GB.

The rubrics (`evals/tasks/small-rubric.md`, `evals/tasks/rubric.md`) hold the pitfalls to catch and measured
answers. They are not copied here, and no prompt of the loop may contain them. A run is graded against them by
reading its trace: whether each pitfall was caught and the definition and limits stated, not only whether a number
matches. A right answer may be one the agent is the first to compute.
