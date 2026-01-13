from database import get_db
from models import User
from middleware.auth import pwd_context
from sqlalchemy.orm import Session

db: Session = next(get_db())
user = db.query(User).filter(User.username == 'denzylibe6').first()
if user:
    print(f'User: {user.username}')
    print(f'Hashed password: {user.hashed_password}')

    # Test with different passwords
    test_passwords = ['testpassword123', 'password', '123456', 'denzylibe6']
    for pwd in test_passwords:
        result = pwd_context.verify(pwd, user.hashed_password)
        print(f'Password "{pwd}" verification: {result}')
else:
    print('User not found')
