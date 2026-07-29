from dotenv import load_dotenv
import os

load_dotenv()

print(os.getenv("TOKEN_SPTRANS"))
print(os.getenv("TOKEN_WEATHER"))