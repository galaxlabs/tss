frappe.ui.form.on("Trip", {
	refresh(frm) {
		set_trip_queries(frm);
		set_default_schedule(frm);
		add_trip_buttons(frm);
		add_passenger_tools(frm);
	},
	onload(frm) {
		set_trip_queries(frm);
		set_default_schedule(frm);
	},
	trip_booking(frm) {
		if (!frm.doc.trip_booking) {
			return;
		}
		frappe.db.get_doc("Trip Booking", frm.doc.trip_booking).then((booking) => {
			frm.set_value("base_company", booking.base_company);
			frm.set_value("route", booking.route);
			frm.set_value("pricing_rule", booking.pricing_rule);
			frm.set_value("customer_name", booking.passenger_name);
			frm.set_value("mobile_no", booking.mobile_no);
			frm.set_value("passenger_count", booking.seat_count || (booking.booking_passenger || []).length || 1);
		});
	},
	driver(frm) {
		if (!frm.doc.driver) {
			return;
		}
		frappe.db.get_doc("Staff", frm.doc.driver).then((staff) => {
			if (staff.assigned_vehicle && !frm.doc.vehicle) {
				frm.set_value("vehicle", staff.assigned_vehicle);
			}
		});
	},
	route(frm) {
		sync_route_arrival(frm);
	},
	departure_datetime(frm) {
		sync_route_arrival(frm);
	}
});

function set_trip_queries(frm) {
	frm.set_query("driver", () => ({
		filters: {
			base_company: frm.doc.base_company,
			staff_type: "Driver",
			status: "Active"
		}
	}));

	frm.set_query("co_driver", () => ({
		filters: {
			base_company: frm.doc.base_company,
			staff_type: "Driver",
			status: "Active"
		}
	}));

	frm.set_query("trip_booking", () => ({
		filters: {
			base_company: frm.doc.base_company
		}
	}));

	frm.set_query("vehicle", () => {
		const filters = {
			base_company: frm.doc.base_company,
			status: "Active"
		};
		if (frm.doc.driver) {
			filters.assigned_driver = frm.doc.driver;
		}
		return { filters };
	});
}

function set_default_schedule(frm) {
	if (frm.is_new() && !frm.doc.departure_datetime) {
		frm.set_value("departure_datetime", frappe.datetime.now_datetime());
	}
	if (frm.is_new() && !frm.doc.arrival_datetime) {
		frm.set_value("arrival_datetime", frm.doc.departure_datetime || frappe.datetime.now_datetime());
	}
}

function sync_route_arrival(frm) {
	if (!frm.doc.route || !frm.doc.departure_datetime) {
		return;
	}
	frappe.db.get_value("Route", frm.doc.route, "estimated_duration_minutes").then((r) => {
		const minutes = Number((r.message && r.message.estimated_duration_minutes) || 0);
		const departure = frappe.datetime.str_to_obj(frm.doc.departure_datetime);
		departure.setMinutes(departure.getMinutes() + minutes);
		frm.set_value("arrival_datetime", frappe.datetime.obj_to_str(departure));
	});
}

function add_trip_buttons(frm) {
	if (frm.__trip_buttons_added) {
		return;
	}
	frm.__trip_buttons_added = true;

	frm.add_custom_button(__("Duplicate Trip"), () => create_new_trip_from(frm, { mode: "duplicate" }));
	frm.add_custom_button(__("Return Trip"), () => create_new_trip_from(frm, { mode: "return" }));
	frm.add_custom_button(__("Extend Trip"), () => show_extend_trip_dialog(frm));

	if (!frm.doc.__islocal && frm.doc.trip_booking) {
		frm.add_custom_button(__("Open Booking"), () => {
			frappe.set_route("Form", "Trip Booking", frm.doc.trip_booking);
		});
		frm.add_custom_button(__("Pull Booking Passengers"), () => {
			frappe.call({
				method: "tss.tss.doctype.trip.trip.pull_passengers_from_booking",
				args: { trip_name: frm.doc.name },
				callback() {
					frm.reload_doc();
				}
			});
		});
	}

	if (!frm.doc.__islocal) {
		frm.add_custom_button(__("Create Return Trip"), () => {
			frappe.call({
				method: "tss.tss.doctype.trip.trip.create_return_trip",
				args: { source_trip: frm.doc.name },
				callback(r) {
					if (r.message) {
						frappe.set_route("Form", "Trip", r.message);
					}
				}
			});
		});
	}

	if (frm.doc.distance_km_snapshot >= 500) {
		frm.set_df_property("co_driver", "reqd", 1);
	} else {
		frm.set_df_property("co_driver", "reqd", 0);
	}
}

function create_new_trip_from(frm, { mode, extend_to_location = null, extend_route = null }) {
	const new_doc = frappe.model.get_new_doc("Trip");
	new_doc.driver = frm.doc.driver || null;
	new_doc.vehicle = frm.doc.vehicle || null;
	new_doc.base_company = frm.doc.base_company || null;
	new_doc.passengers = [];

	(frm.doc.passengers || []).forEach((row) => {
		const child = frappe.model.add_child(new_doc, "Passengers", "passengers");
		child.passenger_name = row.passenger_name;
		child.passenger_name_ar = row.passenger_name_ar;
		child.document_number = row.document_number;
		child.nationality = row.nationality;
		child.mobile_no = row.mobile_no;
		child.document_type = row.document_type;
		child.expiry_date = row.expiry_date;
		child.source = row.source;
		child.seat_no = row.seat_no;
		child.notes = row.notes;
	});

	reset_trip_fields(new_doc);

	if (mode === "return") {
		new_doc.is_return_trip = 1;
		new_doc.from_location = frm.doc.to_location || null;
		new_doc.to_location = frm.doc.from_location || null;
		if (frm.doc.route) {
			frappe.call({
				method: "tss.tss.doctype.route.route.get_or_create_reverse_route",
				args: { route_name: frm.doc.route },
				callback(r) {
					if (r.message && r.message.route) {
						new_doc.route = r.message.route;
					}
					frappe.set_route("Form", "Trip", new_doc.name);
				}
			});
			return;
		}
	}

	if (mode === "extend") {
		new_doc.from_location = frm.doc.to_location || null;
		new_doc.to_location = extend_to_location || null;
		new_doc.route = extend_route || null;
	}

	frappe.set_route("Form", "Trip", new_doc.name);
}

function reset_trip_fields(new_doc) {
	new_doc.qr_code = null;
	new_doc.qr_payload = null;
	new_doc.route = null;
	new_doc.route_label = null;
	new_doc.from_location = null;
	new_doc.to_location = null;
	new_doc.distance_km_snapshot = null;
	new_doc.duration_minutes_snapshot = null;
	new_doc.departure_datetime = frappe.datetime.now_datetime();
	new_doc.arrival_datetime = null;
	new_doc.actual_departure_datetime = null;
	new_doc.actual_arrival_datetime = null;
	new_doc.trip_status = "Scheduled";
	new_doc.kashf_sent = 0;
	new_doc.is_return_trip = 0;
	new_doc.trip_date = frappe.datetime.get_today();
}

function show_extend_trip_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Extend Trip"),
		fields: [
			{
				fieldname: "info",
				fieldtype: "HTML",
				options: `<div><b>From</b> will be current <b>To</b>: ${frappe.utils.escape_html(frm.doc.to_location || "")}</div><br/>`
			},
			{
				fieldname: "extend_route",
				label: __("Select Route"),
				fieldtype: "Link",
				options: "Route"
			},
			{
				fieldname: "extend_to_location",
				label: __("New Destination"),
				fieldtype: "Data"
			}
		],
		primary_action_label: __("Create Extended Trip"),
		primary_action(values) {
			if (!values.extend_route && !values.extend_to_location) {
				frappe.msgprint(__("Please select a Route or enter New Destination."));
				return;
			}
			d.hide();
			create_new_trip_from(frm, {
				mode: "extend",
				extend_to_location: values.extend_to_location || null,
				extend_route: values.extend_route || null
			});
		}
	});
	d.show();
}

function add_passenger_tools(frm) {
	if (!frm.fields_dict.passengers || !frm.fields_dict.passengers.grid || frm._passenger_paste_button_added) {
		return;
	}
	frm._passenger_paste_button_added = true;
	frm.fields_dict.passengers.grid.add_custom_button(__("Paste Passenger List"), () => {
		show_passenger_import_dialog(frm);
	});
}

function show_passenger_import_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Paste Passenger List"),
		fields: [
			{ fieldname: "raw_text", label: __("Passenger list text"), fieldtype: "Small Text", reqd: 1 },
			{ fieldname: "ignore_header", label: __("First row is header"), fieldtype: "Check", default: 1 },
			{ fieldname: "default_nationality", label: __("Default Nationality"), fieldtype: "Data" },
			{
				fieldname: "import_mode",
				label: __("Import mode"),
				fieldtype: "Select",
				options: "Append (add only new rows)\nReplace (clear then import)",
				default: "Append (add only new rows)"
			}
		],
		primary_action(values) {
			const result = parse_passengers_smart((values.raw_text || "").trim(), { ignore_header: !!values.ignore_header });
			if (result.format === "Arabic Name + Number" && !values.default_nationality) {
				frappe.msgprint(__('This format has no nationality. Please fill "Default Nationality".'));
				return;
			}
			if (!result.rows.length) {
				frappe.msgprint(__("No passengers detected."));
				return;
			}
			if ((values.import_mode || "").startsWith("Replace")) {
				frm.clear_table("passengers");
			}
			const existing = new Set((frm.doc.passengers || []).map((row) => make_sig(row.passenger_name, row.document_number, row.nationality)));
			let added = 0;
			for (const p of result.rows) {
				const passenger_name = (p.passenger_name || "").trim();
				const document_number = (p.document_number || "").trim();
				const nationality = (p.nationality || values.default_nationality || "").trim();
				if (!passenger_name || !document_number || !nationality) {
					continue;
				}
				const sig = make_sig(passenger_name, document_number, nationality);
				if ((values.import_mode || "").startsWith("Append") && existing.has(sig)) {
					continue;
				}
				const row = frm.add_child("passengers");
				row.passenger_name = passenger_name;
				row.document_number = document_number;
				row.nationality = nationality;
				row.mobile_no = p.contact_no || "";
				existing.add(sig);
				added += 1;
			}
			frm.refresh_field("passengers");
			d.hide();
			frappe.msgprint(__("Imported {0} passenger(s). Detected format: {1}", [added, result.format]));
		}
	});
	d.show();
}

function make_sig(name, doc, nat) {
	return [(doc || "").toUpperCase(), (name || "").toUpperCase(), (nat || "").toUpperCase()].join("|");
}

function parse_passengers_smart(input, opts) {
	const text = normalize_text(input);
	const arabicBlocks = parse_arabic_blocks_multi(text);
	if (arabicBlocks.rows.length) return arabicBlocks;
	const arabicSimple = parse_arabic_name_number_lines(text);
	if (arabicSimple.rows.length) return arabicSimple;
	if (looks_like_markdown_table(text)) return parse_markdown_table(text, opts.ignore_header);
	if (text.includes("\t")) return parse_delimited_lines(text, "\t", opts.ignore_header, "TSV");
	if (text.includes(",")) return parse_delimited_lines(text, ",", opts.ignore_header, "CSV");
	return parse_english_regex(text);
}

function normalize_text(value) {
	return (value || "").replace(/\r/g, "").replace(/\n{3,}/g, "\n\n").trim();
}

function clean_spaces(value) {
	return (value || "").replace(/\s+/g, " ").trim();
}

function normalize_digits(value) {
	const map = { "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9" };
	return (value || "").replace(/[٠-٩]/g, (d) => map[d] || d);
}

function parse_arabic_blocks_multi(text) {
	const blocks = text.split(/\n\s*\n/g).map((b) => b.trim()).filter(Boolean);
	const rows = [];
	for (const block of blocks) {
		if (!/الجنسية\s*[:：]/.test(block)) continue;
		const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
		const nameLine = lines.find((l) => !/[：:]/.test(l) && !/^الجنسية\b/.test(l) && !/^رقم\b/.test(l) && !/^هوية\b/.test(l)) || "";
		const natMatch = block.match(/الجنسية\s*[:：]\s*([^\n]+)/);
		const docMatch = block.match(/(رقم\s*الجواز|رقم\s*الاقامة|رقم\s*الإقامة|هوية\s*زائر)\s*[:：]\s*([0-9٠-٩A-Z]+)/i);
		if (!nameLine || !natMatch || !docMatch) continue;
		rows.push({ passenger_name: clean_spaces(nameLine), nationality: clean_spaces(natMatch[1]), document_number: normalize_digits(docMatch[2] || "").trim() });
	}
	return { format: "Arabic Blocks", rows };
}

function parse_arabic_name_number_lines(text) {
	if (text.includes("|") || text.includes(",") || text.includes("\t")) return { format: "Arabic Name + Number", rows: [] };
	const rows = [];
	for (const lineRaw of text.split("\n").map((l) => l.trim()).filter(Boolean)) {
		const match = lineRaw.match(/([0-9٠-٩]{7,15})\s*$/);
		if (!match) continue;
		rows.push({
			passenger_name: clean_spaces(lineRaw.slice(0, match.index).trim()),
			document_number: normalize_digits(match[1] || "").trim(),
			nationality: ""
		});
	}
	return { format: "Arabic Name + Number", rows };
}

function looks_like_markdown_table(text) {
	return text.split("\n").filter((l) => l.includes("|")).length >= 2 && /---/.test(text);
}

function parse_markdown_table(text, ignore_header) {
	let lines = text.split("\n").filter((l) => l.includes("|") && !/^\s*\|?\s*-{2,}/.test(l));
	if (ignore_header && lines.length > 1) lines = lines.slice(1);
	return {
		format: "Markdown Table",
		rows: lines.map((line) => {
			const parts = line.split("|").map((x) => x.trim()).filter(Boolean);
			return { passenger_name: parts[0], document_number: parts[1], nationality: parts[2], contact_no: parts[3] || "" };
		}).filter((row) => row.passenger_name && row.document_number && row.nationality)
	};
}

function parse_delimited_lines(text, delim, ignore_header, formatName) {
	let lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
	if (ignore_header && lines.length > 1) lines = lines.slice(1);
	return {
		format: formatName,
		rows: lines.map((line) => {
			const parts = line.split(delim).map((p) => (p || "").trim()).filter((p) => p !== "");
			return { passenger_name: parts[0], document_number: parts[1], nationality: parts[2], contact_no: parts[3] || "" };
		}).filter((row) => row.passenger_name && row.document_number && row.nationality)
	};
}

function parse_english_regex(text) {
	const stream = text.replace(/\n/g, " ");
	const regex = /([A-Za-z][A-Za-z\s.-]{1,60}?)\s*([A-Z]{1,2}\d{6,}|\d{7,})\s*([A-Za-z]{3,}(?:\s+[A-Za-z]{3,})?)/g;
	const rows = [];
	let match;
	while ((match = regex.exec(stream)) !== null) {
		rows.push({ passenger_name: clean_spaces(match[1] || ""), document_number: (match[2] || "").trim(), nationality: clean_spaces(match[3] || "") });
	}
	return { format: "Regex (merged text)", rows };
}
