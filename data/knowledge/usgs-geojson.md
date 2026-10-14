# How to interpret the USGS GeoJSON feed

The USGS GeoJSON feed publishes a collection of detected events. Each feature contains an event
identifier, a geometry ordered as longitude, latitude and depth, and properties such as magnitude,
place, event time, update time, review status and a link to the event page.

The `time` field describes when the earthquake occurred. The `updated` field records when USGS last
changed the published record. This application adds `ingested_at`, which records when our system
learned about that version. Keeping the three timestamps separate allows a historical answer to
exclude revisions that were not yet known at its knowledge cutoff.

The `felt` value counts submitted Did You Feel It? reports; it is not an intensity value or a count
of everyone who felt the earthquake. The `tsunami` flag is a USGS processing indicator, not an
evacuation order. A missing `alert` value does not prove that an event caused no damage.

Official source: USGS GeoJSON Summary Format.
https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
