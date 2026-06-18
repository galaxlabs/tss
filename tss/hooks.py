app_name = "tss"
app_title = "TSS"
app_publisher = "Galaxy Labs"
app_description = "Transport Service System"
app_email = "galaxylab2020@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["gbase"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "tss",
# 		"logo": "/assets/tss/logo.png",
# 		"title": "TSS",
# 		"route": "/tss",
# 		"has_permission": "tss.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tss/css/tss.css"
# app_include_js = "/assets/tss/js/tss.js"

# include js, css files in header of web template
# web_include_css = "/assets/tss/css/tss.css"
# web_include_js = "/assets/tss/js/tss.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "tss/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "tss/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "tss.utils.jinja_methods",
# 	"filters": "tss.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "tss.setup.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "tss.uninstall.before_uninstall"
# after_uninstall = "tss.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "tss.utils.before_app_install"
# after_app_install = "tss.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "tss.utils.before_app_uninstall"
# after_app_uninstall = "tss.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tss.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Staff": {
		"before_validate": "tss.utils.staff_setup.apply_transport_staff_defaults",
		"after_insert": "tss.utils.staff_setup.ensure_transport_staff_links",
		"on_update": "tss.utils.staff_setup.ensure_transport_staff_links",
	},
	"Trip": {
		"on_update": "tss.utils.pdf_hooks.create_trip_pdf",
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"tss.tasks.all"
# 	],
# 	"daily": [
# 		"tss.tasks.daily"
# 	],
# 	"hourly": [
# 		"tss.tasks.hourly"
# 	],
# 	"weekly": [
# 		"tss.tasks.weekly"
# 	],
# 	"monthly": [
# 		"tss.tasks.monthly"
# 	],
# }

# Testing
# -------

before_tests = "tss.setup.install.after_migrate"
boot_session = "tss.override_frappe_get_pdf"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "tss.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Vehicle": "tss.tss.doctype.vehicle.vehicle_dashboard.get_data",
	"Route": "tss.tss.doctype.route.route_dashboard.get_data",
	"Trip": "tss.tss.doctype.trip.trip_dashboard.get_data",
	"Trip Booking": "tss.tss.doctype.trip_booking.trip_booking_dashboard.get_data",
	"Trip Pricing Rule": "tss.tss.doctype.trip_pricing_rule.trip_pricing_rule_dashboard.get_data",
	"Vehicle Inspection Log": "tss.tss.doctype.vehicle_inspection_log.vehicle_inspection_log_dashboard.get_data",
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["tss.utils.before_request"]
# after_request = ["tss.utils.after_request"]

# Job Events
# ----------
# before_job = ["tss.utils.before_job"]
# after_job = ["tss.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"tss.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

fixtures = [
	{"dt": "Print Format", "filters": [["module", "=", "TSS"]]},
]

after_migrate = ["tss.setup.install.after_migrate", "tss.override_frappe_get_pdf"]
