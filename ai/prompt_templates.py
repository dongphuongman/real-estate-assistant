from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PromptTemplateVariable:
    name: str
    description: str
    required: bool = True
    example: str | None = None


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    title: str
    category: str
    description: str
    template_text: str
    variables: tuple[PromptTemplateVariable, ...]


_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _extract_placeholders(text: str) -> set[str]:
    return {m.group(1) for m in _PLACEHOLDER_RE.finditer(text)}


def get_prompt_templates() -> list[PromptTemplate]:
    return list(_TEMPLATES)


def get_prompt_template_by_id(template_id: str) -> PromptTemplate | None:
    for tmpl in _TEMPLATES:
        if tmpl.id == template_id:
            return tmpl
    return None


def render_prompt_template(
    template: PromptTemplate, variables: Mapping[str, Any]
) -> str:
    declared_vars = {v.name: v for v in template.variables}

    unknown_vars = sorted(set(variables.keys()) - set(declared_vars.keys()))
    if unknown_vars:
        raise ValueError(f"Unknown variables: {', '.join(unknown_vars)}")

    missing_required = [
        v.name
        for v in template.variables
        if v.required and not _is_non_empty_string(variables.get(v.name))
    ]
    if missing_required:
        raise ValueError(f"Missing required variables: {', '.join(missing_required)}")

    placeholders = _extract_placeholders(template.template_text)
    undeclared_placeholders = sorted(placeholders - set(declared_vars.keys()))
    if undeclared_placeholders:
        raise ValueError(
            f"Template contains undeclared placeholders: {', '.join(undeclared_placeholders)}"
        )

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = variables.get(name)
        if value is None:
            return ""
        return str(value).strip()

    rendered = _PLACEHOLDER_RE.sub(_replace, template.template_text)
    return _cleanup_rendered(rendered)


def _cleanup_rendered(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


_TEMPLATES: tuple[PromptTemplate, ...] = (
    PromptTemplate(
        id="listing_description_v1",
        title="Listing description (friendly)",
        category="listing_description",
        description="Generates a concise listing description with key highlights and a clear CTA.",
        template_text=(
            "Write a listing description for the property below.\n\n"
            "Property:\n"
            "- Address/Area: {{area}}\n"
            "- Type: {{property_type}}\n"
            "- Size: {{area_sqm}} m²\n"
            "- Rooms: {{rooms}}\n"
            "- Price: {{price}}\n"
            "- Key features: {{features}}\n\n"
            "Tone: friendly, clear, non-salesy.\n"
            "Constraints:\n"
            "- 120–180 words\n"
            "- Use short paragraphs\n"
            "- End with a call-to-action to schedule a viewing\n"
        ),
        variables=(
            PromptTemplateVariable(
                name="area",
                description="Neighborhood or area (e.g., 'Krakow, Kazimierz').",
                example="Krakow, Kazimierz",
            ),
            PromptTemplateVariable(
                name="property_type",
                description="Property type (e.g., apartment, house).",
                example="apartment",
            ),
            PromptTemplateVariable(
                name="area_sqm",
                description="Size in square meters.",
                example="55",
            ),
            PromptTemplateVariable(
                name="rooms",
                description="Number of rooms.",
                example="2",
            ),
            PromptTemplateVariable(
                name="price",
                description="Price with currency.",
                example="650,000 PLN",
            ),
            PromptTemplateVariable(
                name="features",
                description="Comma-separated key features (balcony, parking, etc.).",
                example="balcony, elevator, parking spot",
            ),
        ),
    ),
    PromptTemplate(
        id="buyer_followup_email_v1",
        title="Buyer follow-up email",
        category="email",
        description="Follow-up email after an inquiry with next steps and a short question set.",
        template_text=(
            "Subject: Quick follow-up on {{property_address}}\n\n"
            "Hi {{buyer_name}},\n\n"
            "Thanks for reaching out about {{property_address}}. "
            "I’d be happy to help.\n\n"
            "A few quick questions so I can tailor options:\n"
            "1) Your preferred move-in timeline?\n"
            "2) Must-haves (e.g., balcony, parking, elevator)?\n"
            "3) Target budget range?\n\n"
            "If you’d like, we can schedule a short viewing call or an in-person visit. "
            "What times work best for you this week?\n\n"
            "Best regards,\n"
            "{{agent_name}}\n"
        ),
        variables=(
            PromptTemplateVariable(
                name="property_address",
                description="Property address or short reference name.",
                example="Main St 10, Warsaw",
            ),
            PromptTemplateVariable(
                name="buyer_name",
                description="Recipient name.",
                example="Alex",
            ),
            PromptTemplateVariable(
                name="agent_name",
                description="Sender name.",
                example="Maria Nowak",
            ),
        ),
    ),
    PromptTemplate(
        id="viewing_request_email_v1",
        title="Viewing request email",
        category="email",
        description="Email requesting a viewing with two time slots and required info.",
        template_text=(
            "Subject: Viewing request — {{property_address}}\n\n"
            "Hello,\n\n"
            "I’m interested in viewing {{property_address}}. "
            "Would either of these times work?\n"
            "- {{slot_1}}\n"
            "- {{slot_2}}\n\n"
            "If not, please suggest a couple of alternatives. "
            "Also, could you confirm any requirements (ID, deposit terms, etc.)?\n\n"
            "Thank you,\n"
            "{{requester_name}}\n"
            "{{requester_phone}}\n"
        ),
        variables=(
            PromptTemplateVariable(
                name="property_address",
                description="Property address or listing reference.",
                example="Kazimierz, Krakow (2-bed)",
            ),
            PromptTemplateVariable(
                name="slot_1",
                description="First proposed time slot.",
                example="Wed 18:00",
            ),
            PromptTemplateVariable(
                name="slot_2",
                description="Second proposed time slot.",
                example="Thu 12:30",
            ),
            PromptTemplateVariable(
                name="requester_name",
                description="Your name.",
                example="Alex",
            ),
            PromptTemplateVariable(
                name="requester_phone",
                description="Phone number (optional).",
                required=False,
                example="+48 123 456 789",
            ),
        ),
    ),
)

_TEMPLATE_IDS = [t.id for t in _TEMPLATES]
if len(_TEMPLATE_IDS) != len(set(_TEMPLATE_IDS)):
    raise RuntimeError("Duplicate prompt template IDs detected")

