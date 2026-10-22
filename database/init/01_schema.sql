
CREATE TABLE emergency_events (
	id VARCHAR(36) NOT NULL, 
	external_id VARCHAR(160), 
	source VARCHAR(80) NOT NULL, 
	type VARCHAR(60) NOT NULL, 
	severity VARCHAR(30) NOT NULL, 
	certainty VARCHAR(30) NOT NULL, 
	urgency VARCHAR(30) NOT NULL, 
	latitude FLOAT, 
	longitude FLOAT, 
	radius_km FLOAT, 
	magnitude FLOAT, 
	depth_km FLOAT, 
	is_test BOOLEAN NOT NULL, 
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ends_at TIMESTAMP WITH TIME ZONE, 
	raw_payload TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_emergency_events_type ON emergency_events (type);

CREATE INDEX ix_emergency_events_source ON emergency_events (source);

CREATE INDEX ix_emergency_events_external_id ON emergency_events (external_id);

CREATE INDEX ix_emergency_events_is_test ON emergency_events (is_test);


CREATE TABLE official_source_syncs (
	id VARCHAR(36) NOT NULL, 
	source VARCHAR(80) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	last_success_at TIMESTAMP WITH TIME ZONE, 
	last_cutoff_date VARCHAR(120), 
	records_count INTEGER, 
	details TEXT, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_official_source_syncs_source ON official_source_syncs (source);


CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	full_name VARCHAR(160) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash TEXT NOT NULL, 
	is_minor BOOLEAN NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE UNIQUE INDEX ix_users_email ON users (email);


CREATE TABLE audit_logs (
	id VARCHAR(36) NOT NULL, 
	actor_user_id VARCHAR(36), 
	action VARCHAR(120) NOT NULL, 
	resource_type VARCHAR(80), 
	resource_id VARCHAR(60), 
	result VARCHAR(30) NOT NULL, 
	reason TEXT, 
	metadata_json TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_actor_user_id ON audit_logs (actor_user_id);


CREATE TABLE consent_policies (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	event_type VARCHAR(60) NOT NULL, 
	requires_official_event BOOLEAN NOT NULL, 
	quorum_required INTEGER NOT NULL, 
	allow_exact_location BOOLEAN NOT NULL, 
	allow_recent_route BOOLEAN NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_consent_policies_user_id ON consent_policies (user_id);


CREATE TABLE devices (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	platform VARCHAR(30) NOT NULL, 
	device_name VARCHAR(120) NOT NULL, 
	push_token TEXT, 
	last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_devices_user_id ON devices (user_id);


CREATE TABLE disappearance_cases (
	id VARCHAR(36) NOT NULL, 
	subject_user_id VARCHAR(36) NOT NULL, 
	opened_by_user_id VARCHAR(36) NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(subject_user_id) REFERENCES users (id), 
	FOREIGN KEY(opened_by_user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_disappearance_cases_opened_by_user_id ON disappearance_cases (opened_by_user_id);

CREATE INDEX ix_disappearance_cases_subject_user_id ON disappearance_cases (subject_user_id);


CREATE TABLE notifications (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	type VARCHAR(60) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	body TEXT NOT NULL, 
	channel VARCHAR(30) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	metadata_json TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	sent_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_notifications_status ON notifications (status);

CREATE INDEX ix_notifications_type ON notifications (type);

CREATE INDEX ix_notifications_user_id ON notifications (user_id);


CREATE TABLE personal_safety_sessions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	sampling_boost_until TIMESTAMP WITH TIME ZONE, 
	notify_contacts_json TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_personal_safety_sessions_user_id ON personal_safety_sessions (user_id);


CREATE TABLE trusted_contacts (
	id VARCHAR(36) NOT NULL, 
	owner_user_id VARCHAR(36) NOT NULL, 
	contact_user_id VARCHAR(36), 
	contact_name VARCHAR(160) NOT NULL, 
	contact_email VARCHAR(254) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	can_receive_sos BOOLEAN NOT NULL, 
	can_view_checkpoint BOOLEAN NOT NULL, 
	can_request_welfare BOOLEAN NOT NULL, 
	quorum_weight INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_user_id) REFERENCES users (id), 
	FOREIGN KEY(contact_user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_trusted_contacts_owner_user_id ON trusted_contacts (owner_user_id);

CREATE INDEX ix_trusted_contacts_contact_user_id ON trusted_contacts (contact_user_id);


CREATE TABLE checkpoints (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	device_id VARCHAR(36), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	synced_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	encrypted_location TEXT NOT NULL, 
	coarse_lat FLOAT NOT NULL, 
	coarse_lon FLOAT NOT NULL, 
	accuracy_m FLOAT, 
	battery_pct FLOAT, 
	network_type VARCHAR(40), 
	movement_state VARCHAR(40), 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	incident_hold BOOLEAN NOT NULL, 
	hold_expires_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(device_id) REFERENCES devices (id)
)

;

CREATE INDEX ix_checkpoints_user_id ON checkpoints (user_id);

CREATE INDEX ix_checkpoints_incident_hold ON checkpoints (incident_hold);

CREATE INDEX ix_checkpoints_created_at ON checkpoints (created_at);

CREATE INDEX ix_checkpoints_expires_at ON checkpoints (expires_at);


CREATE TABLE institutional_references (
	id VARCHAR(36) NOT NULL, 
	case_id VARCHAR(36) NOT NULL, 
	source VARCHAR(80) NOT NULL, 
	reference_number VARCHAR(160) NOT NULL, 
	status VARCHAR(80) NOT NULL, 
	external_url TEXT, 
	reported_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES disappearance_cases (id)
)

;

CREATE INDEX ix_institutional_references_case_id ON institutional_references (case_id);


CREATE TABLE welfare_checks (
	id VARCHAR(36) NOT NULL, 
	subject_user_id VARCHAR(36) NOT NULL, 
	requester_user_id VARCHAR(36), 
	event_id VARCHAR(36), 
	status VARCHAR(40) NOT NULL, 
	reason TEXT, 
	requested_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	quorum_required INTEGER NOT NULL, 
	quorum_count INTEGER NOT NULL, 
	last_checkpoint_id VARCHAR(36), 
	PRIMARY KEY (id), 
	FOREIGN KEY(subject_user_id) REFERENCES users (id), 
	FOREIGN KEY(requester_user_id) REFERENCES users (id), 
	FOREIGN KEY(event_id) REFERENCES emergency_events (id), 
	FOREIGN KEY(last_checkpoint_id) REFERENCES checkpoints (id)
)

;

CREATE INDEX ix_welfare_checks_subject_user_id ON welfare_checks (subject_user_id);

CREATE INDEX ix_welfare_checks_requester_user_id ON welfare_checks (requester_user_id);

CREATE INDEX ix_welfare_checks_status ON welfare_checks (status);


CREATE TABLE community_verifications (
	id VARCHAR(36) NOT NULL, 
	welfare_check_id VARCHAR(36) NOT NULL, 
	verifier_user_id VARCHAR(36) NOT NULL, 
	result VARCHAR(60) NOT NULL, 
	approximate_distance_m INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(welfare_check_id) REFERENCES welfare_checks (id), 
	FOREIGN KEY(verifier_user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_community_verifications_welfare_check_id ON community_verifications (welfare_check_id);

CREATE INDEX ix_community_verifications_verifier_user_id ON community_verifications (verifier_user_id);


CREATE TABLE safety_statuses (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	event_id VARCHAR(36), 
	welfare_check_id VARCHAR(36), 
	status VARCHAR(40) NOT NULL, 
	message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(event_id) REFERENCES emergency_events (id), 
	FOREIGN KEY(welfare_check_id) REFERENCES welfare_checks (id)
)

;

CREATE INDEX ix_safety_statuses_status ON safety_statuses (status);

CREATE INDEX ix_safety_statuses_user_id ON safety_statuses (user_id);


CREATE TABLE welfare_confirmations (
	id VARCHAR(36) NOT NULL, 
	welfare_check_id VARCHAR(36) NOT NULL, 
	contact_user_id VARCHAR(36) NOT NULL, 
	response VARCHAR(40) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(welfare_check_id) REFERENCES welfare_checks (id), 
	FOREIGN KEY(contact_user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_welfare_confirmations_contact_user_id ON welfare_confirmations (contact_user_id);

CREATE INDEX ix_welfare_confirmations_welfare_check_id ON welfare_confirmations (welfare_check_id);