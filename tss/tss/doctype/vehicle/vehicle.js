// Copyright (c) 2026, Galaxy Labs and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle", {
	vehicle_model(frm) {
		if (!frm.doc.vehicle_model) return;

		frappe.db.get_doc("Vehicle Model", frm.doc.vehicle_model).then((model) => {
			frm.set_value("vehicle_make", model.vehicle_make || "");
			frm.set_value("vehicle_type", model.vehicle_type || "");
			frm.set_value("vehicle_category", model.vehicle_category || "");

			if (!frm.doc.seat_capacity && model.seat_capacity) {
				frm.set_value("seat_capacity", model.seat_capacity);
			}
			if (!frm.doc.fuel_type && model.fuel_type) {
				frm.set_value("fuel_type", model.fuel_type);
			}
		});
	}
});
