from fastapi import FastAPI

app=FastAPI()

@app.get('/')
def home():
    return {"message":"Plain get Res Hello All"}

@app.get("/user/{name}")
def get_user(name:str):
    return {"message":name}
