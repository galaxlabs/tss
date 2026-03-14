frappe.ui.form.on("Trip Booking", {
	refresh(frm) {
		frm.set_query("trip", () => ({
			filters: {
				base_company: frm.doc.base_company
			}
		}));

		if (frm.doc.trip) {
			frm.add_custom_button(__("Open Trip"), () => {
				frappe.set_route("Form", "Trip", frm.doc.trip);
			});
		} else if (!frm.is_new()) {
			frm.add_custom_button(__("Create Trip"), () => {
				frappe.call({
					method: "tss.tss.doctype.trip_booking.trip_booking.create_trip_from_booking",
					args: { booking_name: frm.doc.name },
					callback(r) {
						if (r.message) {
							frm.set_value("trip", r.message);
							frappe.set_route("Form", "Trip", r.message);
						}
					}
				});
			});
		}
	},
	trip(frm) {
		if (!frm.doc.trip) {
			return;
		}
		frappe.db.get_doc("Trip", frm.doc.trip).then((trip) => {
			frm.set_value("route", trip.route);
			if (trip.pricing_rule) {
				frm.set_value("pricing_rule", trip.pricing_rule);
			}
		});
	}
});
