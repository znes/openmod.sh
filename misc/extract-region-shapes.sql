SELECT region_key as region_key,
    stat_levl_ as nuts_state_level,
    u_region_id as nuts_id, 
    ST_SetSRID(ST_AsText(geom), 4326) as wkt_polygon, 
    ST_SetSRID(ST_AsText(geom_point), 4326) as wkt_point 
FROM parameter_region, distribution_urid_to_nuts 
WHERE u_region_id LIKE '%DEF%' AND  
	u_region_id = distribution_urid_to_nuts.nuts_id;

