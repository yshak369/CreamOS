from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "CreamOS API is running"}
