from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth_routes, user_routes
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

origins = [
    "https://localhost:3000",  # Frontend origin
    "http://localhost:3000",   # Alternative origin for testing
    # Add more origins as necessary
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Update with allowed methods
    allow_headers=["*"],  # Update with allowed headers if needed
)

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
