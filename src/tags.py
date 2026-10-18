"""Tag spelling fixes and the HC -> cornerstone mapping.

Rule for the family of a tag:
  1. course-prefixed tags (b110-, cs162-, cp-, ...) are LOs
  2. otherwise, the Year 1 cornerstone course (FA, EA, MC, CX) where I used the
     tag most often, if that course has >= 2 uses and is a clear winner
  3. otherwise the handbook table below
"""
from __future__ import annotations
import re

ALIASES = {
    "levelofanalysis": "levelsofanalysis",
    "persuassion": "persuasion",
    "utilities": "utility",
    "sourcequality": "sourcequality",
    "cp196qualitydeliverables": "cp-qualitydeliverables",
}

LO_PREFIX = re.compile(r"^(b\d{3}|cs\d{3}|cp\d{3}|cp|fa\d{2}|ea\d{2}|mc\d{2}|cx\d{2}|gl\d{2}|fe\d{2}|pr\d{2})([\-_]|$)")

HANDBOOK_FAMILY = {
    # Formal Analyses
    **{t: "FA" for t in ["algorithms","optimization","variables","descriptivestats","correlation","regression",
                         "probability","distributions","confidenceintervals","significance","estimation","induction",
                         "deduction","fallacies","utility","decisiontrees","gametheory","modeling","scenarios",
                         "statisticalinference","dataviz","leastsquares","expectedvalue"]},
    # Empirical Analyses
    **{t: "EA" for t in ["rightproblem","breakitdown","gapanalysis","constraints","heuristics","evidencebased",
                         "plausibility","hypothesisdevelopment","testability","sampling","observationalstudy",
                         "interventionalstudy","interviewsurvey","comparisongroups","biasidentification",
                         "biasmitigation","scienceoflearning","casestudy","analogies","contrarian","constraintsatisfaction"]},
    # Multimodal Communications
    **{t: "MC" for t in ["audience","thesis","organization","composition","expression","critique","connotation",
                         "context","medium","multimedia","communicationdesign","interpretivelens","designthinking",
                         "persuasion","professionalism","responsibility","sourcequality","genre","signaling"]},
    # Complex Systems
    **{t: "CX" for t in ["systemmapping","complexcausality","emergentproperties","networks","levelsofanalysis",
                         "systemdynamics","multiagent","negotiate","conflict","powerdynamics","differences",
                         "leadprinciples","ethicalconsiderations","ethicalcourage","ethicaljudgment","purpose",
                         "strategize","selfawareness","emotionaliq","shapingbehavior","conformity",
                         "psychologicalexplanation","nudge","carrotandstick","socialnorms"]},
}
FAMILY_NAMES = {"FA": "Formal Analyses", "EA": "Empirical Analyses", "MC": "Multimodal Communications",
                "CX": "Complex Systems", "LO": "Course learning outcome"}

def normalise(tag: str) -> str:
    t = tag.lower().strip("-_ ")
    return ALIASES.get(t, t)

def is_lo(tag: str) -> bool:
    return bool(LO_PREFIX.match(tag))

def family_from_usage(tag: str, usage: dict) -> str | None:
    """usage: {cornerstone_code: count} for this tag, cornerstone_code in FA/EA/MC/CX."""
    if not usage:
        return None
    best = max(usage.values())
    winners = [k for k, v in usage.items() if v == best]
    if best >= 2 and len(winners) == 1:
        return winners[0]
    return None

def family(tag: str, usage: dict | None = None) -> str:
    if is_lo(tag):
        return "LO"
    return family_from_usage(tag, usage or {}) or HANDBOOK_FAMILY.get(tag, "UNK")

# Plain-English forms of HC names, used for leak masking (condition "masked").
def name_words(tag: str) -> list[str]:
    """Split a camel/concatenated hashtag into likely English words for masking.
    e.g. 'breakitdown' -> ['break it down'], 'evidencebased' -> ['evidence based', 'evidence-based']"""
    manual = {
        "breakitdown": ["break it down", "breaking it down", "broke it down", "break down", "breaking down"],
        "evidencebased": ["evidence based", "evidence-based", "evidence"],
        "rightproblem": ["right problem"], "gapanalysis": ["gap analysis", "gap"],
        "levelsofanalysis": ["levels of analysis", "level of analysis", "multi-level", "multilevel"],
        "systemmapping": ["system mapping", "system map", "systems map"],
        "complexcausality": ["complex causality", "causality", "causal"],
        "emergentproperties": ["emergent properties", "emergent property", "emergence", "emergent"],
        "descriptivestats": ["descriptive statistics", "descriptive stats"],
        "confidenceintervals": ["confidence intervals", "confidence interval"],
        "hypothesisdevelopment": ["hypothesis development", "hypothesis"],
        "biasidentification": ["bias identification", "bias"], "biasmitigation": ["bias mitigation", "bias"],
        "interviewsurvey": ["interview", "survey"], "scienceoflearning": ["science of learning"],
        "communicationdesign": ["communication design"], "interpretivelens": ["interpretive lens"],
        "designthinking": ["design thinking"], "ethicalconsiderations": ["ethical considerations", "ethical"],
        "ethicalcourage": ["ethical courage"], "ethicaljudgment": ["ethical judgment", "ethical judgement"],
        "leadprinciples": ["lead principles", "leadership principles"], "powerdynamics": ["power dynamics"],
        "selfawareness": ["self awareness", "self-awareness"], "emotionaliq": ["emotional iq", "emotional intelligence"],
        "shapingbehavior": ["shaping behavior", "shaping behaviour"], "systemdynamics": ["system dynamics"],
        "psychologicalexplanation": ["psychological explanation"], "observationalstudy": ["observational study"],
        "interventionalstudy": ["interventional study"], "comparisongroups": ["comparison groups"],
        "dataviz": ["data visualization", "data visualisation", "visualization", "visualisation"],
        "multimedia": ["multimedia", "multi-media"], "sourcequality": ["source quality"],
        "decisiontrees": ["decision trees", "decision tree"], "gametheory": ["game theory"],
    }
    if tag in manual:
        return manual[tag] + [tag]
    return [tag]
