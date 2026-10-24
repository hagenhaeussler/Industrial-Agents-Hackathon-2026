Use `spatial_query` for spatial facts instead of reading geometry yourself.
Use `room_stacked` with `target` and `direction=above|below`.
Use `shared_walls_count` with `target` for adjacent room counts.
Use `straight_line_3d` with `target` and `second_target` for a direct distance.
Use `errand` with start (`target`), `asset_type`, `floor` and `room_type`.
Use `what_if_door` with both rooms and the counted floor for an exit comparison.
These are computed queries. They do not change the building.
Report the result with its meaning and unit. Do not guess a missing value.
