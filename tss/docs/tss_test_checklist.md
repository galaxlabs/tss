# TSS Test Checklist

## Masters

- `Vehicle Category`, `Vehicle Type`, `Vehicle Make`, and `Vehicle Model` save with cleaned values and generated codes.
- `Vehicle Model` rejects mismatched category/type relationships.

## Vehicle

- Active vehicle cannot be saved under inactive `Base Company`.
- Duplicate `plate_no`, `chassis_no`, `engine_no`, and `registration_no` are blocked.
- Assigned driver must be `Staff.staff_type = Driver`.
- Document rows reject duplicates and invalid issue/expiry order.

## Route

- Source and destination cannot match.
- Route stop sequence duplicates are blocked.
- Route stop names are normalized and duplicate stops are blocked.

## Pricing

- Amount must be positive.
- `effective_to` cannot be before `effective_from`.
- Company consistency works with linked route.

## Trip

- Trip requires company, route, vehicle, driver, date, and departure.
- Vehicle and driver overlap detection blocks conflicting active trips.
- `available_seats` recalculates from active bookings.
- Hijri date and QR payload are generated.

## Booking

- Booking requires trip and passenger name.
- Seat count cannot exceed trip availability.
- Duplicate passenger document numbers and duplicate seat numbers in one booking are blocked.
- Fare amount must be positive.

## Inspection

- Inspection requires company, vehicle, date, and at least one item.
- Inspection trip vehicle must match selected vehicle.
- Overall result derives from row results.
- Checklist rows auto-fill from active checklist master rows.

## Print

- `Trip Manifest` renders QR image and Hijri date.
- `Vehicle Inspection` renders current inspection schema fields.

## Regression

- Dashboard navigation opens linked documents with correct fields.
- `Transport Settings` singleton can be created during install/migrate.
- Existing API modules are reviewed before client rollout because some still reflect pre-redesign field names.
