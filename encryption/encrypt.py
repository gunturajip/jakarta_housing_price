from cryptography.fernet import Fernet
import json

# Generate a key
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Load and encrypt the JSON data
with open("jakarta-housing-price-595a9cff2797.json", "r") as file:
    data = json.load(file)
    json_data = json.dumps(data)
    encrypted_data = cipher_suite.encrypt(json_data.encode())

# Save the encrypted data to a file
with open("encrypted_data.bin", "wb") as file:
    file.write(encrypted_data)

print(f"Encryption key: {key.decode()}")