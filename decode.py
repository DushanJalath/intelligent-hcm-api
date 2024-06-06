import jwt


SECRET_KEY = "INTELECRAFTERS"
ALGORITHM = "HS256"

token = "$2b$12$gEQ/CLrYFB52KrFotauOyuaEvQck/aCt6mJFrxAbWePCt6c/zauqG"



decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
print("Decoded Token:", decoded_token)

