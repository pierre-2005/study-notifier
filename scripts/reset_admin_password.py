"""Local operator-only emergency recovery, intended for docker exec -it.
Never pass passwords as shell arguments (they appear in process history).
"""
import getpass
import sys
from app.auth import get_user_by_username, update_user_password

def main():
    if len(sys.argv)!=2:
        print('Usage: python -m scripts.reset_admin_password <admin_username>')
        return 2
    user=get_user_by_username(sys.argv[1])
    if not user or user['role']!='admin':
        print('Administrator not found.')
        return 1
    one=getpass.getpass('New temporary administrator password (12+ chars): ')
    two=getpass.getpass('Confirm new password: ')
    if one!=two or len(one)<12 or len(one)>256:
        print('Passwords must match and contain 12-256 characters.')
        return 1
    update_user_password(user['id'],one,actor_id=user['id'],temporary=True)
    print('Administrator password reset. Existing sessions are revoked; sign in and change password.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
