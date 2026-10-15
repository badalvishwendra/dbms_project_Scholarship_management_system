import uvicorn
from backend.app import app

if __name__ == "__main__":
    uvicorn.run("run:app", reload=True)
