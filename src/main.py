from fastapi import FastAPI
from src.controllers.pdf_controller import router as pdf_router
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

app.include_router(pdf_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}
