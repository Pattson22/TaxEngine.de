from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.deductions import router as deductions_router
from app.api.routes.tax_filings import router as tax_filings_router
from app.api.routes.users import router as users_router
from app.api.routes.wage_tax_certificates import router as wage_tax_certificates_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(wage_tax_certificates_router)
api_router.include_router(deductions_router)
api_router.include_router(tax_filings_router)
