# Uncertainty and earthquake revisions

The first published solution uses the observations available at that moment. As more stations and
analyst reviews become available, USGS may revise origin time, location, depth, magnitude,
magnitude type and derived products. A revision is an updated estimate, not evidence that the
previous record was fraudulent.

A temporal application must distinguish `occurred_at`, `source_updated_at` and `ingested_at`.
Overwriting the previous row would destroy the ability to reconstruct what the application knew
before a revision. Historical queries must not leak a later version into an earlier answer.

Displaying many decimal places does not create scientific certainty. Coordinates and depth depend
on the station network, velocity model and signal quality. The application can show exactly what
changed, but the feed alone may not explain why analysts revised it.

Official sources: USGS Earthquake Hazards Program and GeoJSON feed documentation.
https://www.usgs.gov/programs/earthquake-hazards
