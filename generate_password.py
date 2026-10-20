import getpass
import bcrypt
password=getpass.getpass("Yönetici şifresi: ")
print(bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode())
