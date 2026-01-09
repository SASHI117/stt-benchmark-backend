from dotenv import load_dotenv
load_dotenv()

from database import engine

print("DB engine:", engine)
