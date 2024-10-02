from enum import Enum
from dataclasses import dataclass

@dataclass
class Role:
    name: str

class Assistant(Enum):
    RESUME_ANALYST = Role(
        "Resume Analyst",
    )

    @property
    def role_details(self):
        return {
            'name': self.value.name,
        }
