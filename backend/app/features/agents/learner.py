"""Find candidate norms across cases. No tools and no authority to publish them."""

from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, RunContext

from app.features.learning.schemas import LearningOutput


@dataclass(frozen=True)
class Deps:
    references: set[str]
    existing: set[str]


learner = Agent(None, output_type=LearningOutput, deps_type=Deps, retries=2, name="learner")


@learner.output_validator
def validate(ctx: RunContext[Deps], result: LearningOutput) -> LearningOutput:
    texts = set()
    for proposal in result.proposals:
        refs = set(proposal.evidence + proposal.counterexamples)
        if refs - ctx.deps.references:
            raise ModelRetry("Cite only evidence references supplied in the analysis context")
        text = proposal.text.casefold().strip()
        if text in texts or text in ctx.deps.existing:
            raise ModelRetry("Do not repeat an existing norm or another proposal")
        texts.add(text)
    for change in result.definition_changes:
        if set(change.evidence) - ctx.deps.references:
            raise ModelRetry("Cite only evidence references supplied in the analysis context")
        if change.kind != "context" and not change.name:
            raise ModelRetry(f"A {change.kind} change needs its snake_case name")
        if change.kind == "input" and not change.type:
            raise ModelRetry("An input change needs the symbol's type")
    return result
