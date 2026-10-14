# USGS earthquake products

Did You Feel It? collects questionnaires describing how people experienced an earthquake. The
reports help map perceived intensity, including places without dense instrumentation. The feed's
`felt` field is a response count and is influenced by population, internet access and participation.

ShakeMap produces near-real-time maps of ground motion and shaking intensity by combining
instrumental observations, models and available information. PAGER provides rapid estimates of
exposure and possible consequences for significant earthquakes. Its alert levels are not
equivalent to magnitude or the `tsunami` flag.

If a product is absent, the correct conclusion is that it is unavailable in the consulted context.
The application must not turn `null` into "no damage", "not felt" or "no risk".

Official sources: USGS Earthquakes, ShakeMap and GeoJSON Summary Format.
https://earthquake.usgs.gov/data/products/
