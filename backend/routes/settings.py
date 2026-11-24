from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Setting
from backend.schemas import SettingsResponse, SettingsUpdate

router = APIRouter()

DEFAULT_SETTINGS = {
    "camera_device": "0",
    "confidence_threshold": "0.6",
    "session_timeout": "30"
}

@router.get("/", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    settings_db = {s.key: s.value for s in db.query(Setting).all()}
    
    # Merge with defaults
    for k, v in DEFAULT_SETTINGS.items():
        if k not in settings_db:
            settings_db[k] = v
            # Save default to db
            db.add(Setting(key=k, value=v))
    db.commit()
            
    return SettingsResponse(
        camera_device=settings_db["camera_device"],
        confidence_threshold=float(settings_db["confidence_threshold"]),
        session_timeout=int(settings_db["session_timeout"])
    )

@router.post("/", response_model=SettingsResponse)
def update_settings(settings_update: SettingsUpdate, db: Session = Depends(get_db)):
    updates = settings_update.dict(exclude_unset=True)
    for key, value in updates.items():
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = str(value)
        else:
            db.add(Setting(key=key, value=str(value)))
    
    db.commit()
    return get_settings(db=db)
