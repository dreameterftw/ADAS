# External data connectors

The service keeps external credentials on the backend. Set the following variables in the Render service environment; do not add them to Firebase/Vite variables.

## Hospital directory (FHIR R4)

- `HOSPITAL_FHIR_BASE_URL`: FHIR server base URL. The adapter reads active `Location` and `HealthcareService` resources and associates services with locations.
- `HOSPITAL_FHIR_BEARER_TOKEN`: optional bearer token, if the server requires one.
- `FHIR_BED_COUNT_EXTENSION_URL`: provider-defined numeric extension URL for currently available beds. Core FHIR Location and HealthcareService do not define live bed availability; without this extension, imported facilities are not considered available for dispatch.
- `FHIR_TOTAL_BED_COUNT_EXTENSION_URL`: optional provider-defined numeric extension URL for total capacity.

Locations require WGS84 latitude/longitude. Specialty terms are normalized to trauma, cardiac, or general. The adapter snaps facility coordinates to the nearest node in the active road graph.

## Ambulance positions (AVL)

- `AMBULANCE_FEED_URL`: authenticated JSON endpoint.
- `AMBULANCE_FEED_BEARER_TOKEN`: optional bearer token.

The feed can be a top-level array or an object containing an `ambulances`, `vehicles`, `items`, or `value` array. Each record requires `id`, `latitude` (or `lat`), and `longitude` (or `lon`/`lng`); `status` is optional and defaults to available. The accepted status values for an available unit are `available`, `idle`, `ready`, and `active`. Other statuses are treated as unavailable. Coordinates are snapped to the active road graph, and the unit list is replaced by the received feed at each successful sync.

## Operations

- `GET /operations/integrations` reports configured sources.
- `POST /operations/sync` fetches configured hospital and ambulance data and replans after successful updates.
- `PUT /operations/traffic` accepts `{"mode":"normal"}`, `{"mode":"peak"}`, or `{"mode":"event"}`. These modes use the built-in scenario traffic weights. Live traffic routing requires a separate provider adapter and server-side credentials.
- `POST /operations/scenario/showcase` resets the map to the repeatable multi-incident, multi-ambulance presentation scenario.

Provider feeds must be authorized for the service account and must not contain patient-identifying data. The request log and simulation state are in memory and reset when the backend restarts.
