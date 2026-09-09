from __future__ import annotations

from app.models import GenerationCreate


class PromptBuilder:
    DEFAULT_NEGATIVE = (
        "identity drift",
        "distorted anatomy",
        "duplicate person",
        "text or watermark",
        "low-resolution face",
    )

    def build(self, request: GenerationCreate, reference_count: int) -> str:
        identity = (
            "Preserve the same adult person's recognizable facial identity across the result. "
            if request.preserve_identity
            else "Use the references only for general visual direction. "
        )
        negatives = list(dict.fromkeys([*self.DEFAULT_NEGATIVE, *request.negative_constraints]))
        return " ".join(
            [
                f"Create one {request.style} image in {request.aspect_ratio} format.",
                f"Scene: {request.scene.strip()}.",
                f"Use {reference_count} authorized reference image(s).",
                identity,
                "Avoid: " + ", ".join(negatives) + ".",
                "Return a natural, coherent photograph suitable for human review.",
            ]
        )

