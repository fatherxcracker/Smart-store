-- Sample data for testing / the demo. Replace the UPC/EPC values with the
-- codes your real barcode labels and RFID tags return when scanned.
INSERT OR IGNORE INTO products (name, category, price, upc, epc, producer, expiry_date) VALUES
 ('Coca-Cola 500ml',          'Beverage',  2.49, '049000042566', 'E28011700000020A1B2C3D01', 'Coca-Cola Company',   '2027-06-30'),
 ('Lay''s Classic Chips 235g','Snacks',    4.99, '060410013410', 'E28011700000020A1B2C3D02', 'PepsiCo',             '2027-02-15'),
 ('Natrel Milk 2% 2L',        'Dairy',     5.79, '068700100147', 'E28011700000020A1B2C3D03', 'Agropur',             '2026-11-20'),
 ('Kit Kat 45g',              'Candy',     1.99, '059800000154', 'E28011700000020A1B2C3D04', 'Nestle',              '2027-09-01'),
 ('Dasani Water 591ml',       'Beverage',  1.79, '067000004114', 'E28011700000020A1B2C3D05', 'Coca-Cola Company',   '2028-01-01');

INSERT INTO receptions (product_id, quantity, note)
SELECT id, 24, 'Initial stock' FROM products
WHERE NOT EXISTS (SELECT 1 FROM receptions);
