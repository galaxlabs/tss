# TSS Migration Notes

## Legacy to redesigned mapping

- `tms.Route` -> `tss.Route`
  Keep source, destination, distance, duration.
  Drop city-code and duplicated route title fields.
  Normalize to `route_name`, `source`, `destination`, `route_stops`.

- `tms.Vehicle Pricing` -> `tss.Trip Pricing Rule`
  Keep company, route, vehicle type, effectivity, amount.
  Drop legacy mixed pricing flags until they are intentionally reintroduced.

- `tms.Trip` -> `tss.Trip`
  Keep QR, Hijri date, route defaults, trip timing.
  Drop customer-request fields from the trip core.
  Normalize assignment to `vehicle`, `driver`, `conductor`, `trip_staff`.

- `tms.Trip Booking` -> `tss.Trip Booking`
  Keep passenger and fare capture.
  Redesign around a required `trip`, seat count, and booking state.

- `tms.Vehicle Inspection Log` -> `tss.Vehicle Inspection Log`
  Keep checklist pattern.
  Normalize to `inspector`, `inspection_type`, `overall_result`, and item `result`.

## Data cleanup rules

- Uppercase and normalize `registration_no`, `chassis_no`, `engine_no`, and `plate_no`.
- Map legacy `assigned_vehicle` to `vehicle`.
- Map legacy `assigned_driver` to `driver`.
- Map legacy `co_driver` to `trip_staff` row with role `Driver` or `Assistant` based on client data.
- Map legacy passenger rows into `Passengers` and keep `seat_no` where present.
- Recompute `available_seats` after importing bookings.

## Recommended migration sequence

1. Import `Vehicle Category`, `Vehicle Type`, `Vehicle Make`, `Vehicle Model`.
2. Import `Route` and optional `Route Stop`.
3. Import `Vehicle`.
4. Import `Trip Pricing Rule`.
5. Import `Trip`.
6. Import `Trip Booking`.
7. Import `Vehicle Inspection Log`.

## Post-migration checks

- Verify no duplicate vehicle identifiers remain.
- Verify every active trip vehicle and driver belong to the same `Base Company`.
- Verify booking seat totals do not exceed trip seat capacity.
- Verify print formats render on migrated Trip and Vehicle Inspection Log records.
