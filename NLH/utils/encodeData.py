import base64

def encodePassword(user_id: str, password: str) -> str:
    validate_code = "qazwsx"
    encode_step1 = base64.b64encode(password.encode()).decode()
    encode_step2 = base64.b64encode((encode_step1 + user_id).encode()).decode()

    encode_final = base64.b64encode((encode_step2 + validate_code).encode()).decode()
    return encode_final