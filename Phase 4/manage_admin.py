"""Grant or revoke inventory administrator access for an existing account."""
import argparse
import db

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('email', help='Email of an existing account')
parser.add_argument('--revoke', action='store_true', help='Remove administrator access')
args = parser.parse_args()
db.init_db()
with db.get_connection() as conn:
    result = conn.execute('UPDATE customers SET is_admin = ? WHERE email = ?',
                          (0 if args.revoke else 1, args.email.strip().lower()))
    if result.rowcount != 1:
        parser.error('Account not found. Register it through the website first.')
print('Administrator access ' + ('removed.' if args.revoke else 'granted.'))
