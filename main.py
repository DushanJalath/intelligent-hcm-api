from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth_routes, user_routes, products_routes,claim_bill_routes,approve_bill_route
from fastapi.security import OAuth2PasswordBearer
import utils

app = FastAPI()

origins = [
    "https://localhost:3000",  
    "http://localhost:3000",   

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  
    allow_headers=["*"],  
)

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(products_routes.router)
app.include_router(claim_bill_routes.router)
app.include_router(approve_bill_route.router)
    
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
