// Copyright (c) 2026, Galaxy Labs and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Model", {
	vehicle_type(frm) {
		if (!frm.doc.vehicle_type) return;

		frappe.db.get_doc("Vehicle Type", frm.doc.vehicle_type).then((vehicle_type) => {
			frm.set_value("vehicle_category", vehicle_type.category || "");
			if (!frm.doc.seat_capacity && vehicle_type.default_seating_capacity) {
				frm.set_value("seat_capacity", vehicle_type.default_seating_capacity);
			}
		});
	}
});
