# TSS Transport Blueprint

## 1. Architecture overview

TSS is a standalone transport domain app anchored on GBase `Base Company` and `Staff`. It separates transport into masters, planning, operations, compliance, and configuration layers and keeps print, QR, Hijri, and validation logic in shared utilities.

## 2. Comparison notes from old TMS vs new TSS

- Keep: route defaults, QR and Hijri support, inspection checklist behavior, print payload concepts
- Redesign: company-aware routes, trip-linked bookings, effectivity-based pricing, normalized vehicle identity, reusable validations
- Drop: mixed hospitality scope, weak field naming, duplicate company/staff models, loose booking models

## 3. Final doctype list

- Vehicle Category
- Vehicle Type
- Vehicle Make
- Vehicle Model
- Route
- Route Stop
- Vehicle
- Trip Pricing Rule
- Trip
- Trip Staff Assignment
- Trip Booking
- Passengers
- Vehicle Inspection Log
- Vehicle Inspection Log Item
- Vehicle Inspection Checklist Item
- Transport Settings

## 4. Dashboard link design

- Vehicle -> Trip, Vehicle Inspection Log, assigned Driver, default Route
- Route -> Trip, Trip Booking, Trip Pricing Rule
- Trip Pricing Rule -> Route, Vehicle Type, linked Trips and Bookings
- Trip -> Trip Booking, Vehicle, Route, Vehicle Inspection Log, Staff
- Trip Booking -> Trip plus Route, Vehicle, Driver, and pricing navigation
- Vehicle Inspection Log -> Vehicle, Trip, Inspector

## 5. Permission model

TSS uses GBase access control instead of separate app-specific roles.

- Use the existing GBase operational roles and role profiles already assigned to users
- Use `Staff.staff_type` as the transport behavior anchor: `Admin`, `Operations`, `Driver`, `Mechanic`, `Supervisor`, `Booking`, `Basic`
- Apply `Base Company` user permissions for company segregation
- Restrict driver users to their own `Staff` record and assigned trips where needed
- Keep TSS transport doctypes permissioned through the same client-specific GBase security model rather than introducing `TSS Admin` or other duplicate roles
- Recommended matrix:
  `Admin` and `Operations` can manage all transport masters and transactions
  `Supervisor` can review trips, pricing, bookings, and inspections across their company
  `Booking` can create and update bookings and read trip, route, and pricing context
  `Driver` can read assigned trips, vehicle context, and their own inspection-linked records
  `Mechanic` can manage inspection logs and read vehicles and trips
  `Basic` can have read-only access where the client needs limited visibility

## 6. Setup and seed strategy

- Create `Transport Settings` during install or migrate
- Reuse GBase users, roles, and role profiles directly
- Seed print formats and inspection defaults through fixtures
- Keep seed logic minimal and client-safe:
  create only singleton/config documents that TSS itself owns
  never create transport users or roles automatically
  rely on GBase onboarding to provision staff, linked users, and role profiles

## 7. Fixtures strategy

- Print Format
- Property Setter
- Client Script
- Workspace
- Export only TSS-owned UI artifacts and never duplicate GBase role or profile records
- See [tss_fixtures_strategy.md](/home/dg/db-b/apps/tss/tss/docs/tss_fixtures_strategy.md)

## 8. Test checklist

- Vehicle uniqueness and driver validation
- Route stop ordering and route uniqueness
- Pricing date and company consistency
- Trip vehicle and driver overlap control
- Booking seat availability and seat duplication prevention
- Inspection result derivation and trip consistency
- QR/Hijri and print rendering behavior
- See [tss_test_checklist.md](/home/dg/db-b/apps/tss/tss/docs/tss_test_checklist.md)

## 9. Migration strategy

- `tms.Route` -> `tss.Route`
- `tms.Vehicle Pricing` -> `tss.Trip Pricing Rule`
- `tms.Trip` -> `tss.Trip`
- `tms.Trip Booking` -> `tss.Trip Booking`
- `tms.Vehicle Inspection Log` -> `tss.Vehicle Inspection Log`
- See [tss_migration_notes.md](/home/dg/db-b/apps/tss/tss/docs/tss_migration_notes.md)

## 10. Phase-2 extension notes

- Dispatch board
- Public booking APIs
- ERPNext bridges
- Automated expiry reminders
