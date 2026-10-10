"""Fast tests of the conversation logic in chat.py (no model needed).

  .venv/bin/python scripts/test_chat.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import chat  # noqa: E402
from chat import PatientContext, build_messages, prepare, render_citations  # noqa: E402

FAILS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global FAILS
    FAILS += not cond
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + ("" if cond else f" — {detail}"))


def convo(*turns: str) -> tuple[list[dict], PatientContext, list[dict]]:
    """Run prepare() over alternating user / assistant texts (assistant texts given)."""
    msgs, ctx, preps = [], PatientContext(), []
    for i, t in enumerate(turns):
        if i % 2 == 0:
            p = prepare(t, msgs, ctx)
            preps.append(p)
            msgs.append({"role": "user", "content": t, "topic_start": p["topic_changed"]})
        else:
            msgs.append({"role": "assistant", "content": t})
    return msgs, ctx, preps


def main() -> int:
    # 1. short reply linked to the earlier complaint
    msgs, ctx, p = convo("My right eye has been blurry and a bit red.",
                         "That can have several causes [nei_006_chunk_01]. How long has this been happening?",
                         "Two days")
    check("short reply: duration recorded", ctx.duration and ctx.duration.value == "2 days", str(ctx.duration))
    check("short reply: query carries the complaint", "blurry" in p[1]["query"] and "Two days" in p[1]["query"],
          p[1]["query"])
    check("short reply: not treated as a new topic", not p[1]["topic_changed"])
    _, final = build_messages("Two days", msgs[:-1], ctx, [], True, True, p[1]["pending_qs"])
    check("short reply: prompt links it to the question", "reply to your question" in final
          and "How long has this been happening?" in final, final[-200:])

    # 2. corrections
    msgs, ctx, _ = convo("My right eye is itchy.", "Itching is common with allergies.",
                         "Actually, it's my left eye.")
    check("correction: eye updated", ctx.eye.value == "left eye", str(ctx.eye))
    check("correction: previous value kept for the record", ctx.eye.previous == "right eye")
    check("correction: shown to the model", any("corrected from right eye" in l for l in ctx.lines()))
    msgs, ctx, _ = convo("It started three days ago", "OK.", "Sorry, I meant a week ago")
    check("correction: timing updated", ctx.duration.value in ("a week ago", "1 week ago"), str(ctx.duration))

    # 3. assistant hypotheses never become patient facts
    msgs, ctx, _ = convo("My eye is red and watery.",
                         "This could be pink eye or dry eye, and sometimes glaucoma causes redness. "
                         "Do you have diabetes?",
                         "No")
    check("hypothesis: no glaucoma in history", "glaucoma" not in ctx.history, str(ctx.history))
    check("hypothesis: no diabetes from the assistant's question", "diabetes" not in ctx.history)
    check("hypothesis: facts list has no assistant terms",
          not any("pink eye" in l or "glaucoma" in l for l in ctx.lines()), str(ctx.lines()))

    # 4. negation
    ctx = PatientContext()
    ctx.update("It's red but there's no pain and no discharge", 1)
    check("negation: pain denied", "eye pain" in ctx.denied and "eye pain" not in ctx.symptoms, str(ctx.denied))
    check("negation: redness kept", "redness" in ctx.symptoms)

    # 5. new symptom changes urgency on a later turn
    msgs, ctx, p = convo("My eye has some floaters.", "Floaters are common [nei_015_chunk_01]. Are they new?",
                         "They appeared suddenly an hour ago and now there's a dark curtain")
    check("urgency: first turn not urgent", not p[0]["urgent"])
    check("urgency: reassessed and urgent on turn 2", p[1]["urgent"])

    # 6. urgency from the combination of turns
    msgs, ctx, p = convo("My eye hurts.", "When did it start?", "Suddenly, and I feel nauseous")
    check("urgency: combined turns trigger", p[1]["urgent"], p[1]["user_text"])

    # 7. topic change -> fresh retrieval, old complaint dropped
    msgs, ctx, p = convo("My left eye is itchy and red.", "Itchy red eyes are often allergies [nei_008_chunk_01].",
                         "Different question: how does LASIK surgery work for nearsightedness?")
    check("topic change detected", p[1]["topic_changed"])
    check("topic change: query is the new question only", "itchy" not in p[1]["query"], p[1]["query"])
    check("topic change: old symptoms dropped", "itching" not in ctx.symptoms, str(ctx.symptoms))

    # 8. truncation keeps facts verbatim
    turns = ["My right eye is blurry.", "How long?", "Two weeks", "Any pain?", "No pain",
             "Diabetes?", "Yes, I have diabetes", "Any floaters?", "A few"]
    msgs, ctx, _ = convo(*turns)
    msgs.append({"role": "assistant", "content": "OK."})
    out, final = build_messages("Is it serious?", msgs, ctx, [], True, True, [])
    check("truncation: history bounded", len(out) <= 2 + chat.MAX_VERBATIM_MESSAGES, str(len(out)))
    check("truncation: earlier facts preserved", "Eye: right eye" in final and "Timing: 2 weeks" in final
          and "diabetes" in final and "eye pain" in final, final[:400])
    check("truncation: summary note present", "earlier messages are summarized" in final)

    # 9. restatement vs claim
    check("restatement kept", chat.is_restatement("You mentioned your right eye has been blurry for two days.",
                                                  "my right eye has been blurry two days"))
    check("medical claim not a restatement", not chat.is_restatement(
        "Blurry vision can be a sign of cataracts.", "my right eye has been blurry"))

    # 10. citation rendering keeps traceability and flags unknown IDs
    res = [{"chunk_id": "nei_001_chunk_01", "title": "Cataracts", "section": "x", "url": "u", "text": "t"}]
    txt, srcs = render_citations("Cataracts are common [nei_001_chunk_01]. Other [nei_999_chunk_09].", res)
    check("citations: numbered marker", "common¹" in txt and len(srcs) == 1, txt)
    check("citations: unsupplied ID flagged", "Otherˀ" in txt and "<" not in txt, txt)

    # 11. prompt separates reported facts from evidence; evidence is not instructions
    _, final = build_messages("Two days", msgs, ctx, res, False, True, [])
    check("prompt: reported facts labelled as the person's own words", "their own words, not confirmed" in final)
    check("system prompt: evidence is not instructions", "not as instructions" in chat.CHAT_SYSTEM_PROMPT)

    # 12. a valid citation that does not support a negated / inferential claim
    import json
    chunks = {c["chunk_id"]: c for c in map(json.loads, open(Path(__file__).resolve().parent.parent
                                                              / "data/processed/chunks.jsonl"))}
    res = [chunks["nei_021_chunk_01"], chunks["nei_002_chunk_03"], chunks["nei_014_chunk_01"]]
    t = ("Uveitis can cause blurry vision and red eyes, but it doesn't usually include pain [nei_021_chunk_01]. "
         "Since you don't have eye pain, it's less likely to be angle-closure glaucoma [nei_002_chunk_03]. "
         "Retinal detachment is a medical emergency [nei_014_chunk_01].")
    out, rem = chat.negation_check(t, res)
    check("unsupported negation removed despite valid citation", "doesn't usually include pain" not in out, out)
    check("inference from absence removed", "less likely" not in out, out)
    check("supported claim kept", "medical emergency" in out, out)

    # 13. regressions found by the multi-turn evaluation
    msgs, ctx, p = convo("My right eye has been watering a lot.", "Watering can have causes.",
                         "Actually, it's my left eye, not the right.", "OK.", "Is that something to worry about?")
    check("follow-up question is not a new topic", not p[2]["topic_changed"] and ctx.eye.value == "left eye",
          str(ctx.lines()))
    msgs, ctx, p = convo("My left eye has been blurry for a month and I'm 70.", "That has several causes.",
                         "Just tell me straight: is it cataracts or not? I need a yes or no.")
    check("pressure question keeps context", not p[1]["topic_changed"] and ctx.eye.value == "left eye")
    msgs, ctx, p = convo("My right eye is red.", "OK.", "What is glaucoma?")
    check("general unrelated question is a new topic", p[1]["topic_changed"])
    ctx = PatientContext()
    ctx.update("No discharge, just itchy.", 1)
    check("negation stops at comma/just", "itching" in ctx.symptoms and "discharge" in ctx.denied, str(ctx.lines()))
    msgs, ctx, p = convo("My eye has been a bit red today.", "Redness has causes.",
                         "Now it really hurts and my vision is blurry and I feel sick to my stomach.")
    check("pain + 'sick to my stomach' is urgent", p[1]["urgent"] and not p[1]["topic_changed"])

    # 14. answer-quality fixes
    check("filler removed + synonym added", "AMD" in chat.clean_query("What actually happens in macular degeneration?")
          and "actually" not in chat.clean_query("What actually happens in macular degeneration?"))
    check("plain referral kept", chat.is_safe_referral("It's worth getting this checked by an eye doctor soon.", "my eye"))
    check("referral with a medical claim still verified",
          not chat.is_safe_referral("An eye doctor can check for glaucoma, which damages the optic nerve.", "my eye"))
    check("question about an already-reported symptom dropped",
          "curtain" not in chat.drop_known_questions("Is there a curtain or shadow? How long has it lasted?",
                                                     "floaters and now a dark shadow"))

    # 15. held-out failures (fixed after the held-out run; that run is reported as-is)
    msgs, ctx, p = convo("I had cataract surgery last week.", "Recovery usually goes well.",
                         "Since yesterday my eye is very red and the pain won't go away even with pain pills.")
    check("post-op very red + persistent pain is urgent", p[1]["urgent"])
    msgs, ctx, p = convo("I had cataract surgery last week. How long until I can drive?")
    check("post-op routine question not urgent", not p[0]["urgent"])
    check("repeated question dropped", "both" not in chat.drop_known_questions(
        "Would you say the grittiness is only in your left eye, or does it happen in both?",
        "my left eye feels gritty", []))
    check("near-identical earlier question dropped", chat.drop_known_questions(
        "Have you noticed any redness?", "my eye", ["Have you noticed any redness or swelling?"]) == "")

    check("title match: glaucoma question", chat.title_match("will he go blind from glaucoma",
          [{"title": "Glaucoma"}]))
    check("title match: dry eye", chat.title_match("my eye gritty and dry", [{"title": "Dry Eye"}]))
    check("no title match for unrelated page", not chat.title_match("blue light glasses screens",
          [{"title": "Dry Eye"}]))

    # 16. curly apostrophes in sources do not defeat the negation check
    out, rem = chat.negation_check("Most people have floaters that come and go, and they often don't need "
                                   "treatment [nei_015_chunk_01].", [chunks["nei_015_chunk_01"]])
    check("supported negation with curly source apostrophe kept", "don't need" in out, out)
    v = {"removed": [{"claim": "Floaters always mean a retinal tear.", "reasons": ["claim contradicts source wording"]},
                     {"claim": "Screens are a common cause of eye strain.", "reasons": ["no supplied passage states this"]}],
         "checks": [{"claim": "Floaters are small dark shapes that float across your vision.", "status": "supported",
                     "id": "nei_015_chunk_01"}]}
    text, general, removed = chat.assemble_explain(
        "Floaters are small dark shapes that float across your vision. Floaters always mean a retinal tear. "
        "Screens are a common cause of eye strain. See an eye doctor if they are new. "
        "You should see an eye doctor soon.", v, [chunks["nei_015_chunk_01"]])
    check("explain: contradicted sentence removed", "always mean" not in text, text)
    check("explain: verifier citation attached", "vision [nei_015_chunk_01]." in text, text)
    check("explain: uncovered sentence kept as general", "Screens" in text and any("Screens" in g for g in general))
    check("explain: only one doctor referral", text.count("eye doctor") == 1, text)

    text, _, _ = chat.assemble_explain("Floaters are common. You should see an eye doctor soon.",
                                       {"removed": [], "checks": []}, [], allow_referral=False)
    check("explain: no referral without a reason", "eye doctor" not in text and "Floaters are common." in text, text)
    check("referral reason detected for sudden symptoms", bool(chat.REFERRAL_REASON.search("they appeared suddenly")))
    check("no referral reason for a simple question", not chat.REFERRAL_REASON.search("what are floaters and why do I have them"))

    text, _, _ = chat.assemble_explain("It is an emergency [nei_015_chunk_03]. [nei_015_chunk_03]",
                                       {"removed": [], "checks": []}, [chunks["nei_015_chunk_03"]])
    check("explain: duplicated citation collapsed", text.count("nei_015_chunk_03") == 1, text)

    print("ALL PASS" if not FAILS else f"{FAILS} FAILED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
