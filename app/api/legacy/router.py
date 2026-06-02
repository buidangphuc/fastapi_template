from fastapi import APIRouter

from app.api.legacy import description, listing, pair_address, usage

router = APIRouter()
router.include_router(usage.router, tags=["Tracking"])
router.include_router(listing.router, tags=["Listing"])
router.include_router(description.router, tags=["Generator"])
router.include_router(pair_address.router, tags=["Generator"])
