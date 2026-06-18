frappe.ui.form.on("Route", {
	refresh(frm) {
		load_google_places(frm);
		sync_route_title(frm);
		if (!frm.is_new()) {
			frm.add_custom_button(__("Fetch Distance"), () => fetch_distance(frm), __("Actions"));
		}
	},
	route_name(frm) {
		sync_route_title(frm);
	},
	route_code(frm) {
		sync_route_title(frm);
	},
	source(frm) {
		if (!frm.doc.route_name && frm.doc.source && frm.doc.destination) {
			frm.set_value("route_name", `${frm.doc.source} - ${frm.doc.destination}`);
		}
		sync_route_title(frm);
	},
	destination(frm) {
		if (!frm.doc.route_name && frm.doc.source && frm.doc.destination) {
			frm.set_value("route_name", `${frm.doc.source} - ${frm.doc.destination}`);
		}
		sync_route_title(frm);
	}
});

function sync_route_title(frm) {
	const routeName = (frm.doc.route_name || "").trim();
	const routeCode = (frm.doc.route_code || "").trim();
	const fallbackName = [frm.doc.source, frm.doc.destination].filter(Boolean).join(" - ");
	const titleName = routeName || fallbackName;
	const routeTitle = [routeCode, titleName].filter(Boolean).join(" | ");

	if (frm.doc.route_title !== routeTitle) {
		frm.set_value("route_title", routeTitle);
	}
}

function fetch_distance(frm) {
	frappe.call({
		method: "tss.tss.doctype.route.route.fetch_distance_for_route",
		args: { route_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Fetching distance..."),
		callback(r) {
			if (r.message) {
				frm.reload_doc();
				frappe.show_alert({ message: __("Distance updated"), indicator: "green" });
			}
		}
	});
}

function load_google_places(frm) {
	if (window.google && window.google.maps && window.google.maps.places) {
		init_route_autocomplete(frm);
		return;
	}

	if (window.__tss_google_places_loading) {
		return;
	}

	window.__tss_google_places_loading = true;
	frappe.call({
		method: "tss.tss.doctype.route.route.get_google_maps_config",
		callback(r) {
			const config = r.message || {};
			if (!config.api_key) {
				window.__tss_google_places_loading = false;
				return;
			}
			const script = document.createElement("script");
			script.src = `https://maps.googleapis.com/maps/api/js?key=${config.api_key}&libraries=places`;
			script.async = true;
			script.onload = () => {
				window.__tss_google_places_loading = false;
				init_route_autocomplete(frm, config.country || "sa");
			};
			script.onerror = () => {
				window.__tss_google_places_loading = false;
				frappe.msgprint(__("Google Places API failed to load. Check key or restrictions."));
			};
			document.head.appendChild(script);
		}
	});
}

function init_route_autocomplete(frm, country = "sa") {
	const options = {
		componentRestrictions: { country: [country] },
		fields: ["name", "formatted_address"]
	};

	bind_place_input(frm, "source", options);
	bind_place_input(frm, "destination", options);
}

function bind_place_input(frm, fieldname, options) {
	const input = frm.fields_dict[fieldname] && frm.fields_dict[fieldname].input;
	if (!input || input.__places_bound || !window.google || !google.maps || !google.maps.places) {
		return;
	}

	const autocomplete = new google.maps.places.Autocomplete(input, options);
	autocomplete.addListener("place_changed", function () {
		const place = autocomplete.getPlace() || {};
		const shortName = (place.name || "").trim();
		if (shortName) {
			frm.set_value(fieldname, shortName);
		}
	});
	input.__places_bound = true;
}
