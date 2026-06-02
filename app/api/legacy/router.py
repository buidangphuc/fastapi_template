from fastapi import APIRouter

from app.api.legacy import description, listing, pair_address, usage

router = APIRouter()
router.include_router(usage.router, tags=["Tracking"])
router.include_router(listing.router, tags=["Listing"])
router.include_router(description.router, tags=["Generator"])
# Legacy nests pair-address under /description -> /api/v1/description/pair_address
router.include_router(pair_address.router, prefix="/description", tags=["Generator"])
