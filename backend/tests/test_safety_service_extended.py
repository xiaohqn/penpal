from app.services.safety_service import SafetyService


def test_detects_implicit_and_real_world_risks():
    service = SafetyService()

    violence = service.assess_user_letter("妈妈生气的时候可能会打我，我不敢回家。")
    assert "family_violence" in violence.categories
    assert violence.handoff == "review"
    assert violence.avoid_in_reply
    assert violence.protective_suggestions

    implicit = service.assess_user_letter("我最近总觉得不想醒来，真的撑不住了。")
    assert "self_harm_metaphor" in implicit.categories
    assert implicit.handoff in {"review", "priority"}

    stalking = service.assess_user_letter("放学后有人一直跟踪我，还威胁要打我。")
    assert "stalking_or_real_world_threat" in stalking.categories
    assert stalking.handoff in {"priority", "urgent"}


def test_does_not_treat_general_parent_conflict_as_violence():
    assessment = SafetyService().assess_user_letter("我和妈妈最近因为学习安排吵了几次。")
    assert "family_violence" not in assessment.categories
