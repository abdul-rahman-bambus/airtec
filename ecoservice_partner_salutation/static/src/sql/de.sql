-- Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
-- See COPYRIGHT and LICENSE at the root directory of this module for full copyright and licensing details.

UPDATE res_partner_title
SET salutation = '{"de_DE": "Sehr geehrte Frau", "en_US": "Dear Mrs."}'
WHERE (name->>'en_US') = 'Madam';

UPDATE res_partner_title
SET salutation = '{"de_DE": "Sehr geehrte Frau", "en_US": "Dear Miss."}'
WHERE (name->>'en_US') = 'Miss';

UPDATE res_partner_title
SET salutation = '{"de_DE": "Sehr geehrter Herr", "en_US": "Dear Mr."}'
WHERE (name->>'en_US') = 'Mister';

UPDATE res_partner_title
SET salutation = '{"de_DE": "Sehr geehrter Herr Dr.", "en_US": "Dear Dr."}'
WHERE (name->>'en_US') = 'Doctor';

UPDATE res_partner_title
SET salutation = '{"de_DE": "Sehr geehrter Herr Professor", "en_US": "Dear Professor"}'
WHERE (name->>'en_US') = 'Professor';
