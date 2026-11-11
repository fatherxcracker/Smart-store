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

-- Demo accounts only. Passwords are hashed; see README for test credentials.
INSERT OR IGNORE INTO customers (name, email, membership_number, password_hash, is_admin) VALUES
 ('Store Admin', 'admin@smartstore.local', 'SS-00000001', 'scrypt:32768:8:1$Thy1i1HmvJkv4lIC$9a4cac4b656b24c8944ed78c10d35f4c810c208b79ce8c766d5875c31884ea45b0e1ca82baad7f5a50c35e5e704ce4b4537e772ed6e1cc6cfc463329b8fbd910', 1),
 ('John', 'john@gmail.com', 'SS-00000002', 'scrypt:32768:8:1$sHcGjoBGGeqSgH0O$205651a9c123a1c40e20064e4b26a8b5987cf98d4fdab1542d570eebcd4603fef737c130b1725cca87539d0a5e7be4dcd87dd40b7326b2fe9aece5d4fffb6cbd', 0);
