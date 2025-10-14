"""High level entry point analogous to ``WebmateAPISession``."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, List, Optional

from .auth import AuthInfo
from .environment import WebmateEnvironment
from .exceptions import WebmateApiError
from .ids import ApplicationModelId, BrowserSessionId, ProjectId, TestSessionId
from .common import Tag

if TYPE_CHECKING:  # pragma: no cover
    from .jobs.engine import JobEngine
    from .browsersession.client import BrowserSessionClient
    from .devices.client import DeviceClient
    from .testmgmt.client import TestMgmtClient
    from .mailtest.client import MailTestClient
    from .artifacts.client import ArtifactClient
    from .images.client import ImageClient
    from .selenium.client import SeleniumServiceClient
    from .blobs.client import BlobClient
    from .packagemgmt.client import PackageMgmtClient


@dataclass
class WebmateSession:
    auth: AuthInfo
    environment: WebmateEnvironment = field(default_factory=WebmateEnvironment)
    project_id: Optional[ProjectId] = None

    def __post_init__(self) -> None:
        from .jobs.engine import JobEngine
        from .browsersession.client import BrowserSessionClient
        from .devices.client import DeviceClient
        from .testmgmt.client import TestMgmtClient
        from .mailtest.client import MailTestClient
        from .artifacts.client import ArtifactClient
        from .images.client import ImageClient
        from .selenium.client import SeleniumServiceClient
        from .blobs.client import BlobClient
        from .packagemgmt.client import PackageMgmtClient

        self.job_engine = JobEngine(self)
        self.browser_session = BrowserSessionClient(self)
        self.device = DeviceClient(self)
        self.test_mgmt = TestMgmtClient(self)
        self.mail_test = MailTestClient(self)
        self.artifact = ArtifactClient(self)
        self.image = ImageClient(self)
        self.selenium = SeleniumServiceClient(self)
        self.blob = BlobClient(self)
        self.packages = PackageMgmtClient(self)

        self._associated_tags: List[Tag] = []
        self._associated_models: List[ApplicationModelId] = []
        self._associated_expeditions: List[BrowserSessionId] = []
        self._associated_test_sessions: List[TestSessionId] = []

    # Session association helpers -------------------------------------------------
    def register_tag(self, *tags: Tag) -> None:
        self._associated_tags.extend(tags)

    def register_model(self, *models: ApplicationModelId) -> None:
        self._associated_models.extend(models)

    def register_browser_session(self, *sessions: BrowserSessionId) -> None:
        self._associated_expeditions.extend(sessions)

    def register_test_session(self, *sessions: TestSessionId) -> None:
        self._associated_test_sessions.extend(sessions)

    # Mirror Java helpers --------------------------------------------------------
    @property
    def associated_tags(self) -> List[Tag]:
        return list(self._associated_tags)

    @property
    def associated_models(self) -> List[ApplicationModelId]:
        return list(self._associated_models)

    @property
    def associated_expeditions(self) -> List[BrowserSessionId]:
        return list(self._associated_expeditions)

    def get_only_associated_expedition(self) -> BrowserSessionId | None:
        if not self._associated_expeditions:
            return None
        if len(self._associated_expeditions) == 1:
            return self._associated_expeditions[0]
        return self._associated_expeditions[-1]

    @property
    def associated_test_sessions(self) -> List[TestSessionId]:
        return list(self._associated_test_sessions)

    def require_project(self) -> ProjectId:
        if not self.project_id:
            raise WebmateApiError("This operation requires a project id")
        return self.project_id


__all__ = ["WebmateSession"]
