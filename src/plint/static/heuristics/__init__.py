"""Registry of all built-in heuristic rules."""

from plint.static.heuristics.prompt_anthropic import (
    PromptExamplesRule,
    PromptLongContextOrderRule,
    PromptNegativeInstructionRule,
    PromptRoleRule,
    PromptSoftEmphasisRule,
    PromptXmlStructureRule,
)
from plint.static.heuristics.prompt_length import PromptLengthRule
from plint.static.heuristics.prompt_procedural import PromptProceduralRule
from plint.static.heuristics.prompt_repetition import PromptRepetitionRule
from plint.static.heuristics.prompt_swears import PromptEmphasisRule
from plint.static.heuristics.separation_overlap import SeparationOverlapRule
from plint.static.heuristics.skill_anthropic import (
    SkillBodySizeRule,
    SkillDescriptionLengthRule,
    SkillForbiddenFilesRule,
    SkillFrontmatterXmlRule,
    SkillKebabCaseRule,
    SkillNameFolderRule,
    SkillNegativeTriggerRule,
    SkillReservedPrefixRule,
)
from plint.static.heuristics.skill_frontmatter import SkillFrontmatterRule
from plint.static.heuristics.skill_specificity import SkillSpecificityRule
from plint.static.heuristics.skill_strict import (
    SkillScriptImportsRule,
    SkillScriptSizeRule,
    SkillSubdirDepthRule,
)
from plint.static.heuristics.tool_description import ToolDescriptionRule
from plint.static.heuristics.tool_quality import (
    ToolExampleRule,
    ToolParamDescriptionRule,
    ToolParamTypeRule,
    ToolUseWhenRule,
)
from plint.static.heuristics.tool_workflow import ToolWorkflowRule
from plint.static.heuristics.xlayer_determinism import XLayerDeterminismRule

ALL_RULES = [
    # Prompt
    PromptLengthRule(),
    PromptRepetitionRule(),
    PromptProceduralRule(),
    PromptEmphasisRule(),
    PromptSoftEmphasisRule(),
    PromptNegativeInstructionRule(),
    PromptRoleRule(),
    PromptXmlStructureRule(),
    PromptExamplesRule(),
    PromptLongContextOrderRule(),
    # Tool
    ToolWorkflowRule(),
    ToolDescriptionRule(),
    ToolExampleRule(),
    ToolUseWhenRule(),
    ToolParamDescriptionRule(),
    ToolParamTypeRule(),
    # Skill
    SkillFrontmatterRule(),
    SkillSpecificityRule(),
    SkillNameFolderRule(),
    SkillDescriptionLengthRule(),
    SkillReservedPrefixRule(),
    SkillFrontmatterXmlRule(),
    SkillForbiddenFilesRule(),
    SkillKebabCaseRule(),
    SkillBodySizeRule(),
    SkillNegativeTriggerRule(),
    # Strict-only (gated on config.strict)
    SkillSubdirDepthRule(),
    SkillScriptSizeRule(),
    SkillScriptImportsRule(),
    # Cross-layer
    SeparationOverlapRule(),
    XLayerDeterminismRule(),
]

__all__ = ["ALL_RULES"]
