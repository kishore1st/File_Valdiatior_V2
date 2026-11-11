-- ============================================================
-- Seed: regions, schema types, schema fields, volume mappings, users
-- ============================================================
INSERT INTO fvi.reference_data (category, key, parent_key, position, value) VALUES
 -- Regions
 ('region','IN', NULL, NULL, '{"name":"India",      "active":true}'),
 ('region','US', NULL, NULL, '{"name":"United States","active":true}'),
 ('region','EU', NULL, NULL, '{"name":"European Union","active":true}'),
 ('region','GB', NULL, NULL, '{"name":"United Kingdom","active":true}'),
 ('region','AE', NULL, NULL, '{"name":"UAE",          "active":true}'),

 -- Schema type: customer (per region)
 ('schema_type','customer','IN', NULL, '{"description":"Customer master","active":true}'),
 ('schema_type','customer','US', NULL, '{"description":"Customer master","active":true}'),
 ('schema_type','customer','EU', NULL, '{"description":"Customer master","active":true}'),
 ('schema_type','customer','GB', NULL, '{"description":"Customer master","active":true}'),
 ('schema_type','customer','AE', NULL, '{"description":"Customer master","active":true}'),

 -- Schema fields (common across regions for MVP)
 ('schema_field','customer_id','IN',1,'{"data_type":"integer","is_mandatory":true}'),
 ('schema_field','first_name', 'IN',2,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','last_name',  'IN',3,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','dob',        'IN',4,'{"data_type":"date",   "is_mandatory":true}'),
 ('schema_field','country',    'IN',5,'{"data_type":"string", "is_mandatory":true,"max_length":2}'),

 ('schema_field','customer_id','US',1,'{"data_type":"integer","is_mandatory":true}'),
 ('schema_field','first_name', 'US',2,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','last_name',  'US',3,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','dob',        'US',4,'{"data_type":"date",   "is_mandatory":true}'),
 ('schema_field','country',    'US',5,'{"data_type":"string", "is_mandatory":true,"max_length":2}'),

 ('schema_field','customer_id','EU',1,'{"data_type":"integer","is_mandatory":true}'),
 ('schema_field','first_name', 'EU',2,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','last_name',  'EU',3,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','dob',        'EU',4,'{"data_type":"date",   "is_mandatory":true}'),
 ('schema_field','country',    'EU',5,'{"data_type":"string", "is_mandatory":true,"max_length":2}'),

 ('schema_field','customer_id','GB',1,'{"data_type":"integer","is_mandatory":true}'),
 ('schema_field','first_name', 'GB',2,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','last_name',  'GB',3,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','dob',        'GB',4,'{"data_type":"date",   "is_mandatory":true}'),
 ('schema_field','country',    'GB',5,'{"data_type":"string", "is_mandatory":true,"max_length":2}'),

 ('schema_field','customer_id','AE',1,'{"data_type":"integer","is_mandatory":true}'),
 ('schema_field','first_name', 'AE',2,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','last_name',  'AE',3,'{"data_type":"string", "is_mandatory":true,"max_length":100}'),
 ('schema_field','dob',        'AE',4,'{"data_type":"date",   "is_mandatory":true}'),
 ('schema_field','country',    'AE',5,'{"data_type":"string", "is_mandatory":true,"max_length":2}'),

 -- Volume mappings
 ('volume_mapping','IN','customer',NULL,'{"volume_path":"/Volumes/main/bronze/incoming/IN/customer/","bronze_table":"main.bronze.customer_in"}'),
 ('volume_mapping','US','customer',NULL,'{"volume_path":"/Volumes/main/bronze/incoming/US/customer/","bronze_table":"main.bronze.customer_us"}'),
 ('volume_mapping','EU','customer',NULL,'{"volume_path":"/Volumes/main/bronze/incoming/EU/customer/","bronze_table":"main.bronze.customer_eu"}'),
 ('volume_mapping','GB','customer',NULL,'{"volume_path":"/Volumes/main/bronze/incoming/GB/customer/","bronze_table":"main.bronze.customer_gb"}'),
 ('volume_mapping','AE','customer',NULL,'{"volume_path":"/Volumes/main/bronze/incoming/AE/customer/","bronze_table":"main.bronze.customer_ae"}')
ON CONFLICT (category, key, parent_key) DO NOTHING;

-- Demo users (replace okta_user_id with real ones in non-local envs)
INSERT INTO fvi.users (okta_user_id, email, display_name, region_code, roles, access_status)
VALUES
 ('okta-admin',   'admin@example.com',   'Admin User',   'IN', ARRAY['admin','approver','uploader','auditor'], 'approved'),
 ('okta-uploader','uploader@example.com','Uploader',     'IN', ARRAY['uploader'], 'approved'),
 ('okta-viewer',  'viewer@example.com',  'Read Only',    'US', ARRAY['auditor'],  'approved')
ON CONFLICT (okta_user_id) DO NOTHING;