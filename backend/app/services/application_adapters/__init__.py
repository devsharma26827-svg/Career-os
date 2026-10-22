from app.services.application_adapters.base import ApplicationResult, BaseApplicationAdapter
from app.services.application_adapters.direct_api_adapter import DirectApiApplicationAdapter
from app.services.application_adapters.email_adapter import EmailApplicationAdapter
from app.services.application_adapters.manual_portal_adapter import ManualPortalRedirectAdapter
from app.services.application_adapters.manager import ApplicationAdapterManager

__all__ = [
    "ApplicationResult",
    "BaseApplicationAdapter",
    "DirectApiApplicationAdapter",
    "EmailApplicationAdapter",
    "ManualPortalRedirectAdapter",
    "ApplicationAdapterManager",
]
