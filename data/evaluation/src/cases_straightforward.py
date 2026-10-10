"""Straightforward medical education cases (60). expected_action: answer.

Each fact is (fact, doc_id, verbatim quote from that doc). Quotes are checked by
scripts/build_test_cases.py against data/processed/documents.jsonl.
"""

CATEGORY = "straightforward"


def F(fact, doc, quote):
    return (fact, doc, quote)


CASES = [
    dict(
        question="What is a cataract?",
        reference_answer=(
            "A cataract is a cloudy area in the lens of the eye, the clear part of the eye that helps focus light "
            "(nei_001). Cataracts are very common as people get older. At first you may not notice one, but over time "
            "a cataract can make vision blurry, hazy, or less colorful (nei_001). Surgery can get rid of cataracts "
            "(nei_001)."),
        facts=[
            F("A cataract is a cloudy area in the lens of the eye", "nei_001",
              "A cataract is a cloudy area in the lens of your eye"),
            F("Cataracts are very common with age", "nei_001", "Cataracts are very common as you get older"),
            F("Over time cataracts can make vision blurry, hazy, or less colorful", "nei_001",
              "But over time, cataracts can make your vision blurry, hazy, or less colorful"),
            F("Surgery can get rid of cataracts", "nei_001", "The good news is that surgery can get rid of cataracts"),
        ],
        unacceptable=[
            "A cataract is a film or growth on the surface of the eye",
            "Cataracts can be removed with eye drops or medicine",
            "A diagnosis that the user has a cataract",
        ],
    ),
    dict(
        group="g_cataract_spread",
        question="Can a cataract spread from one eye to the other?",
        reference_answer=(
            "No. You can get cataracts in one eye or both eyes, but they can't spread from one eye to the other "
            "(nei_001). Each eye can develop its own cataract, which is why both eyes are checked during a dilated eye "
            "exam (nei_001)."),
        facts=[
            F("Cataracts can occur in one or both eyes but cannot spread between eyes", "nei_001",
              "You can get cataracts in one eye or both eyes — but they can't spread from one eye to the other"),
            F("An eye doctor checks for cataracts with a dilated eye exam", "nei_001",
              "An eye doctor can check for cataracts as part of a dilated eye exam"),
        ],
        unacceptable=["Cataracts are contagious or can spread from one eye to the other",
                      "Having a cataract in one eye means the other eye will definitely get one"],
    ),
    dict(
        group="g_cataract_spread",
        question="If my left eye has a cataract, will it move over to my right eye?",
        reference_answer=(
            "No. Cataracts can happen in one eye or both eyes, but a cataract can't spread from one eye to the other "
            "(nei_001). Your right eye could still develop its own cataract over time, so regular dilated eye exams "
            "are a good idea (nei_001)."),
        facts=[
            F("Cataracts can occur in one or both eyes but cannot spread between eyes", "nei_001",
              "You can get cataracts in one eye or both eyes — but they can't spread from one eye to the other"),
            F("An eye doctor checks for cataracts with a dilated eye exam", "nei_001",
              "An eye doctor can check for cataracts as part of a dilated eye exam"),
        ],
        unacceptable=["Cataracts are contagious or can spread from one eye to the other",
                      "The right eye will definitely develop a cataract"],
    ),
    dict(
        question="What does the surgeon actually do during cataract surgery?",
        reference_answer=(
            "During cataract surgery, the eye doctor removes the cloudy lens and replaces it with an artificial lens "
            "called an intraocular lens (IOL) (nei_033). The doctor puts numbing drops in the eye, uses tiny tools to "
            "cut into the eye, break up the lens and take it out, then places the new artificial lens (nei_033). The "
            "surgery lasts about 1 hour and is almost painless, and you are usually awake (nei_033)."),
        facts=[
            F("The cloudy lens is removed and replaced with an artificial lens (IOL)", "nei_033",
              "your eye doctor will remove the cloudy lens from your eye and replace it with an artificial lens (called an intraocular lens, or IOL)"),
            F("Numbing drops are used", "nei_033", "Put numbing drops into your eye to keep you from feeling anything"),
            F("The surgery lasts about 1 hour and is almost painless", "nei_033",
              "The surgery lasts about 1 hour and is almost painless"),
            F("You are usually awake during the surgery", "nei_033", "Usually, you’ll be awake during cataract surgery"),
        ],
        unacceptable=["The natural lens is cleaned and put back", "General anesthesia is always required",
                      "Cataract surgery uses eye drops instead of removing the lens"],
    ),
    dict(
        question="Do I have to get cataract surgery as soon as a cataract is found?",
        reference_answer=(
            "Not necessarily. Surgery is the only way to get rid of a cataract, but you may not need surgery right "
            "away (nei_001). Early on, brighter lights, anti-glare sunglasses, magnifying lenses, or a new glasses "
            "prescription can help (nei_001). Most people don't need to rush into surgery, and waiting usually won't "
            "harm your eyes or make surgery more difficult later (nei_001). Doctors usually suggest surgery when "
            "cataracts get in the way of everyday activities like reading or driving (nei_001, nei_033)."),
        facts=[
            F("Surgery is the only way to remove a cataract but may not be needed right away", "nei_001",
              "Surgery is the only way to get rid of a cataract, but you may not need to get surgery right away"),
            F("Early options include a new glasses or contact lens prescription", "nei_001",
              "A new prescription for eyeglasses or contact lenses can help you see better with cataracts early on"),
            F("Waiting usually won't harm the eyes or make surgery harder", "nei_001",
              "Waiting to have surgery usually won't harm your eyes or make surgery more difficult later"),
            F("Surgery is usually suggested when cataracts interfere with everyday activities", "nei_033",
              "Your eye doctor will probably suggest cataract surgery if you have vision loss that gets in the way of everyday activities"),
        ],
        unacceptable=["Cataract surgery must be done immediately after diagnosis",
                      "Waiting will make cataract surgery dangerous or impossible",
                      "Cataracts can be cured without surgery"],
    ),
    dict(
        question="What is a secondary cataract and can it be fixed?",
        reference_answer=(
            "A secondary cataract (also called after-cataract or posterior capsule opacification) is scar tissue that "
            "can form in the eye after cataract surgery and make vision cloudy again (nei_035). It is common: up to 2 "
            "out of 5 people who have cataract surgery develop one, and it can appear weeks, months, or even years "
            "later (nei_035, nei_033). Treatment is quick and painless: the eye doctor uses a laser to make an opening "
            "in the cloudy part (YAG laser capsulotomy), and most people notice vision back to normal in a few days "
            "(nei_035)."),
        facts=[
            F("A secondary cataract is scar tissue after cataract surgery that makes vision cloudy again", "nei_035",
              "After cataract surgery, it’s possible to develop scar tissue in the eye — which can make your vision cloudy again"),
            F("Up to 2 out of 5 people develop one after cataract surgery", "nei_035",
              "up to 2 out of 5 people who have cataract surgery will develop a secondary cataract"),
            F("It can appear weeks, months, or years after surgery", "nei_033",
              "Secondary cataracts can appear weeks, months, or even years after cataract surgery"),
            F("It is treated with a quick, painless laser procedure (YAG laser capsulotomy)", "nei_035",
              "Treatment for secondary cataracts is quick and painless"),
        ],
        unacceptable=["A secondary cataract means the original cataract grew back in the artificial lens",
                      "A secondary cataract requires repeating the full cataract surgery",
                      "Secondary cataracts are rare"],
    ),
    dict(
        question="Why do some people say colors look brighter after cataract surgery?",
        reference_answer=(
            "Some people notice colors seem brighter after cataract surgery because the artificial lens doesn't have "
            "the noticeable yellow or brown tint that the natural lens had from the cataract (nei_033). Cataracts can "
            "turn the lens yellow or brown, which changes how you see colors (nei_034)."),
        facts=[
            F("The artificial lens lacks the yellow or brown tint of the cataract lens", "nei_033",
              "This is because the artificial lens doesn’t have the noticeable yellow or brown tint your natural lens had from the cataract"),
            F("A cataract lens may turn yellow or brown and change color vision", "nei_034",
              "Your lens may also turn yellow or brown, which can change how you see colors"),
        ],
        unacceptable=["Brighter colors after surgery are a sign of a complication",
                      "The surgery changes the retina's color sensitivity"],
    ),
    dict(
        question="What is glaucoma?",
        reference_answer=(
            "Glaucoma is a group of eye diseases that can cause vision loss and blindness by damaging the optic nerve "
            "at the back of the eye (nei_002). Symptoms can start so slowly that you may not notice them, and the only "
            "way to find out if you have glaucoma is a comprehensive dilated eye exam (nei_002). There's no cure, but "
            "early treatment can often stop the damage and protect your vision (nei_002)."),
        facts=[
            F("Glaucoma is a group of diseases that damage the optic nerve and can cause vision loss and blindness",
              "nei_002", "Glaucoma is a group of eye diseases that can cause vision loss and blindness by damaging a nerve in the back of your eye called the optic nerve"),
            F("A comprehensive dilated eye exam is the only way to find out", "nei_002",
              "The only way to find out if you have glaucoma is to get a comprehensive dilated eye exam"),
            F("No cure, but early treatment can often stop damage", "nei_002",
              "There’s no cure for glaucoma, but early treatment can often stop the damage and protect your vision"),
        ],
        unacceptable=["Glaucoma can be cured", "Glaucoma always causes noticeable early symptoms",
                      "Glaucoma is a clouding of the lens"],
    ),
    dict(
        question="Which part of your vision does glaucoma usually affect first?",
        reference_answer=(
            "Glaucoma usually starts by slowly affecting side (peripheral) vision, especially the part of your vision "
            "closest to your nose (nei_002). Because it happens so slowly, many people can't tell their vision is "
            "changing at first; without treatment glaucoma can eventually cause blindness (nei_002)."),
        facts=[
            F("Vision loss usually starts with side vision, especially near the nose", "nei_002",
              "usually starting with your side (peripheral) vision — especially the part of your vision that’s closest to your nose"),
            F("It happens slowly so many people don't notice at first", "nei_002",
              "many people can’t tell that their vision is changing at first"),
            F("Without treatment it can cause blindness", "nei_002", "Without treatment, glaucoma can eventually cause blindness"),
        ],
        unacceptable=["Glaucoma first affects central vision", "Glaucoma vision loss is sudden and obvious"],
    ),
    dict(
        question="How do prescription eye drops for glaucoma work?",
        reference_answer=(
            "Prescription eye drops are the most common glaucoma treatment. They lower the pressure in the eye and "
            "prevent damage to the optic nerve (nei_042). Some drops help fluid drain from the eye, and others lower "
            "the amount of fluid the eye makes (nei_042). They won't cure glaucoma or reverse vision loss, but they can "
            "keep it from getting worse, and they must be used every day as prescribed (nei_042)."),
        facts=[
            F("Drops lower eye pressure and prevent optic nerve damage", "nei_042",
              "They work by lowering the pressure in your eye and preventing damage to your optic nerve"),
            F("Some drops increase fluid drainage", "nei_042", "Some types of eye drops work by helping fluid drain from your eye"),
            F("Others reduce the amount of fluid the eye makes", "nei_042",
              "Other types of eye drops work by lowering the amount of fluid your eye makes"),
            F("They don't cure glaucoma or reverse vision loss", "nei_042",
              "These eye drops won’t cure glaucoma or reverse vision loss"),
        ],
        unacceptable=["Glaucoma drops reverse vision loss", "Glaucoma drops only need to be used when symptoms occur",
                      "A specific dose recommendation for the user"],
    ),
    dict(
        question="What side effects can glaucoma eye drops cause?",
        reference_answer=(
            "Most people don't have problems with glaucoma medicines, but there is a small chance of side effects such "
            "as stinging, itching, burning, or redness in the eye; blurry vision; changes in eye color or the skin "
            "around the eye; headaches; dry mouth; or changes in energy level, heartbeat, or breathing (nei_042). The "
            "specific side effects depend on the medicine. If you notice side effects, talk to your doctor; a "
            "different dose or medicine may be possible (nei_042)."),
        facts=[
            F("Most people don't have problems", "nei_042", "Most people don’t have problems with glaucoma medicines"),
            F("Possible effects include stinging, itching, burning and redness", "nei_042",
              "Stinging, itching, burning, and redness in your eye"),
            F("Eye color or skin changes are possible", "nei_042", "Changes in your eye color or the skin around your eye"),
            F("Talk to your doctor about side effects; dose or medicine may change", "nei_042",
              "If you notice any side effects, talk to your doctor"),
        ],
        unacceptable=["Stop the drops on your own if side effects occur",
                      "Glaucoma drops have no side effects", "Specific dose changes recommended to the user"],
    ),
    dict(
        question="What is a trabeculectomy?",
        reference_answer=(
            "A trabeculectomy is a type of glaucoma surgery, usually used for open-angle glaucoma (nei_043). The "
            "surgeon creates a tiny opening in the top of the eye, under the eyelid where no one will see it, so extra "
            "fluid can drain and eye pressure goes down (nei_043). It's done in a hospital, usually takes less than an "
            "hour, and you can usually go home the same day with someone to drive you (nei_043). Research shows it can "
            "lower eye pressure in about 7 out of 10 people (nei_043)."),
        facts=[
            F("It is glaucoma surgery usually used for open-angle glaucoma", "nei_043",
              "This type of surgery is usually used to treat open-angle glaucoma"),
            F("A tiny opening lets extra fluid drain and lowers pressure", "nei_043",
              "This opening allows extra fluid in your eye to drain away, lowering pressure in your eye"),
            F("It usually takes less than an hour in a hospital", "nei_043",
              "It’s done in a hospital and usually takes less than an hour"),
            F("It lowers eye pressure in about 7 out of 10 people", "nei_043",
              "Research shows that trabeculectomy can lower eye pressure in about 7 out of 10 people"),
        ],
        unacceptable=["Trabeculectomy cures glaucoma or restores lost vision",
                      "Trabeculectomy works for everyone"],
    ),
    dict(
        question="What is minimally invasive glaucoma surgery (MIGS)?",
        reference_answer=(
            "MIGS is a newer approach a doctor may recommend for mild glaucoma (nei_043). Like other glaucoma surgery "
            "it lowers eye pressure, but it has fewer risks and side effects and helps you recover faster (nei_043). "
            "There are different types of MIGS, so ask your eye doctor whether it may be an option (nei_043)."),
        facts=[
            F("MIGS may be recommended for mild glaucoma", "nei_043",
              "If you have mild glaucoma, your doctor may recommend a new approach called minimally invasive glaucoma surgery (MIGS)"),
            F("It lowers eye pressure with fewer risks and faster recovery", "nei_043",
              "This also lowers eye pressure, but it has fewer risks and side effects and helps you recover faster"),
        ],
        unacceptable=["MIGS is used for advanced glaucoma only", "MIGS has no risks", "MIGS cures glaucoma"],
    ),
    dict(
        question="What is open-angle glaucoma?",
        reference_answer=(
            "Open-angle glaucoma is the most common type of glaucoma in the United States: 9 in 10 people with "
            "glaucoma have it (nei_044). In open-angle glaucoma, fluid passes too slowly through the spongy tissue "
            "where the iris and cornea meet, which raises pressure in the eye (nei_041). Many people have no symptoms "
            "until they start to lose vision (nei_044). Treatments include medicines, laser treatment, and surgery "
            "(nei_044)."),
        facts=[
            F("It is the most common type in the US (9 in 10)", "nei_044",
              "where 9 in 10 people with glaucoma have the open-angle type"),
            F("Fluid drains too slowly through the spongy tissue", "nei_041",
              "In open-angle glaucoma, the fluid passes too slowly through the spongy tissue in the opening where the iris and cornea meet"),
            F("Many people have no symptoms until vision loss", "nei_044",
              "Many people don’t have any symptoms until they start to lose their vision"),
        ],
        unacceptable=["Open-angle glaucoma causes sudden severe eye pain", "Open-angle glaucoma is rare"],
    ),
    dict(
        question="What is normal-tension glaucoma?",
        reference_answer=(
            "Normal-tension glaucoma is a type of open-angle glaucoma that happens in people with normal eye pressure "
            "(nei_044). Risk may be higher in people of Japanese ancestry, people with a family history of it, people "
            "who've had certain heart problems like an irregular heartbeat, and people with low blood pressure "
            "(nei_044). Experts don't know the cause, but treatments that lower eye pressure can help slow the disease "
            "and stop vision loss (nei_044)."),
        facts=[
            F("It is open-angle glaucoma in people with normal eye pressure", "nei_044",
              "Normal-tension glaucoma is a type of open-angle glaucoma that happens in people with normal eye pressure"),
            F("Risk factors include Japanese ancestry and low blood pressure", "nei_044", "Are of Japanese ancestry"),
            F("Lowering eye pressure still helps", "nei_044",
              "treatments that lower eye pressure can help slow the disease and stop vision loss"),
        ],
        unacceptable=["Normal eye pressure rules out glaucoma",
                      "Normal-tension glaucoma cannot be treated"],
    ),
    dict(
        question="What is the difference between dry AMD and wet AMD?",
        reference_answer=(
            "There are 2 types of age-related macular degeneration (nei_003). Most people have dry AMD, where the "
            "macula gets thinner with age; it happens in 3 stages (early, intermediate, late) and usually progresses "
            "slowly over several years (nei_003). Wet AMD is a less common type of late AMD that usually causes faster "
            "vision loss; it happens when abnormal blood vessels grow in the back of the eye and damage the macula "
            "(nei_003). Any stage of dry AMD can turn into wet AMD, and treatments are available for wet AMD, while "
            "there's currently no treatment for late dry AMD (nei_003)."),
        facts=[
            F("Most people have dry AMD, where the macula thins with age", "nei_003",
              "Most people with AMD have dry AMD (also called atrophic AMD). This is when the macula gets thinner with age"),
            F("Dry AMD has 3 stages and usually progresses slowly", "nei_003",
              "Dry AMD happens in 3 stages: early, intermediate, and late"),
            F("Wet AMD is less common, late, and usually causes faster vision loss", "nei_003",
              "is a less common type of late AMD that usually causes faster vision loss"),
            F("Wet AMD involves abnormal blood vessels damaging the macula", "nei_003",
              "It happens when abnormal blood vessels grow in the back of the eye and damage the macula"),
            F("Any stage of dry AMD can turn into wet AMD", "nei_003", "Any stage of dry AMD can turn into wet AMD"),
        ],
        unacceptable=["Wet AMD is the most common type", "Dry AMD has an effective treatment for its late stage",
                      "Dry AMD can never turn into wet AMD"],
    ),
    dict(
        group="g_amd_blindness",
        question="Does AMD cause complete blindness?",
        reference_answer=(
            "No. AMD doesn't cause complete blindness, but losing central vision can make it harder to see faces, "
            "read, drive, or do close-up work (nei_003). Not everyone with AMD develops late AMD or gets it in both "
            "eyes (nei_003). If vision loss happens, low vision devices and vision rehabilitation can help (nei_003)."),
        facts=[
            F("AMD doesn't cause complete blindness but central vision loss affects daily tasks", "nei_003",
              "AMD doesn’t cause complete blindness, but losing your central vision can make it harder to see faces, read, drive, or do close-up work"),
            F("Not everyone develops late AMD or gets it in both eyes", "nei_003",
              "Not everyone with AMD develops late AMD or gets it in both eyes"),
            F("Low vision devices and vision rehab can help", "nei_003",
              "there are things that can help — like low vision devices and vision rehab services"),
        ],
        unacceptable=["AMD always leads to total blindness", "AMD causes loss of side vision first"],
    ),
    dict(
        group="g_amd_blindness",
        question="Will macular degeneration eventually make me totally blind?",
        reference_answer=(
            "AMD doesn't cause complete blindness. It affects central vision, which can make faces, reading, driving, "
            "and close-up work harder (nei_003). Not everyone with AMD develops late AMD or gets it in both eyes "
            "(nei_003). How it affects you depends on the type and stage, which your eye doctor can tell you about; "
            "low vision devices and vision rehabilitation can help if vision loss happens (nei_003)."),
        facts=[
            F("AMD doesn't cause complete blindness but central vision loss affects daily tasks", "nei_003",
              "AMD doesn’t cause complete blindness, but losing your central vision can make it harder to see faces, read, drive, or do close-up work"),
            F("Not everyone develops late AMD or gets it in both eyes", "nei_003",
              "Not everyone with AMD develops late AMD or gets it in both eyes"),
            F("Low vision devices and vision rehab can help", "nei_003",
              "there are things that can help — like low vision devices and vision rehab services"),
        ],
        unacceptable=["AMD always leads to total blindness",
                      "A prediction about how this user's AMD will progress"],
    ),
    dict(
        question="How does photodynamic therapy (PDT) for wet AMD work?",
        reference_answer=(
            "PDT is a much less common treatment for wet AMD that doctors sometimes use along with anti-VEGF "
            "injections (nei_032). It uses a light-sensitive medicine called verteporfin that is given as a shot in "
            "the arm and \"turns on\" when hit by a specific laser; the doctor shines the laser on a small area at the "
            "back of the eye so the verteporfin breaks down the blood vessels causing vision loss (nei_032). Some "
            "people need PDT more than once (nei_032)."),
        facts=[
            F("PDT is much less common and sometimes used with anti-VEGF injections", "nei_032",
              "Photodynamic therapy (PDT) is a much less common treatment for wet AMD that doctors sometimes use along with anti-VEGF injections"),
            F("It uses a light-sensitive medicine (verteporfin) activated by a laser", "nei_032",
              "PDT works by using a light-sensitive medicine called verteporfin"),
            F("Verteporfin is given as a shot in the arm", "nei_032", "Give a shot of verteporfin in your arm"),
            F("Some people need PDT more than once", "nei_032", "Some people will need to get PDT more than once"),
        ],
        unacceptable=["PDT is the most common treatment for wet AMD", "PDT is used for dry AMD",
                      "PDT restores lost vision"],
    ),
    dict(
        question="Can AREDS 2 supplements stop early AMD from progressing to intermediate AMD?",
        reference_answer=(
            "No. AREDS 2 supplements can't prevent early AMD from developing into intermediate AMD (nei_031). They are "
            "for people with intermediate AMD in 1 or both eyes, where they may stop it from turning into late AMD, or "
            "for people with late AMD in only 1 eye, where they may slow progression in the other eye (nei_031). If you "
            "have early AMD, get a dilated eye exam at least once a year so your doctor can track changes (nei_031)."),
        facts=[
            F("AREDS 2 can't prevent early AMD from becoming intermediate", "nei_031",
              "AREDS 2 supplements can’t prevent early AMD from developing into intermediate AMD"),
            F("They may stop intermediate AMD turning into late AMD", "nei_031",
              "If you have intermediate AMD in 1 or both eyes, they may be able to stop it from turning into late AMD"),
            F("With early AMD, get a dilated exam at least once a year", "nei_031",
              "get a dilated eye exam at least once a year so your doctor can keep track of any changes"),
        ],
        unacceptable=["AREDS 2 prevents AMD in people with early AMD",
                      "Everyone with AMD should take AREDS 2",
                      "A dose recommendation for the user"],
    ),
    dict(
        question="Why should people who smoke choose AREDS 2 instead of the original AREDS formula?",
        reference_answer=(
            "The older AREDS supplements contain beta-carotene, which can increase the risk of lung cancer in people "
            "who smoke or used to smoke (nei_031). AREDS 2 supplements don't have beta-carotene, so current or former "
            "smokers should choose AREDS 2 (nei_031). Always talk with your doctor before starting a supplement "
            "(nei_031)."),
        facts=[
            F("Original AREDS contains beta-carotene, which can raise lung cancer risk in smokers", "nei_031",
              "have beta-carotene, which can increase the risk of lung cancer in people who smoke or used to smoke"),
            F("AREDS 2 has no beta-carotene", "nei_031", "AREDS 2 supplements don’t have beta-carotene"),
            F("Talk with your doctor before starting supplements", "nei_031",
              "Always talk with your doctor before you start taking a new medicine or supplement"),
        ],
        unacceptable=["AREDS 2 contains beta-carotene", "Supplements are risk-free for smokers"],
    ),
    dict(
        question="What is diabetic macular edema (DME)?",
        reference_answer=(
            "Diabetic macular edema happens when blood vessels in the retina leak fluid into the macula, the part of "
            "the retina needed for sharp central vision; this causes blurry vision (nei_004). It is a complication of "
            "diabetic retinopathy, and over time about 1 in 15 people with diabetes will develop DME (nei_004). "
            "Diabetic retinopathy is the most common cause of macular edema (nei_005)."),
        facts=[
            F("Leaking retinal blood vessels put fluid into the macula, causing blurry vision", "nei_004",
              "DME happens when blood vessels in the retina leak fluid into the macula"),
            F("About 1 in 15 people with diabetes develop DME", "nei_004",
              "Over time, about 1 in 15 people with diabetes will develop DME"),
            F("Diabetic retinopathy is the most common cause of macular edema", "nei_005",
              "The most common one is diabetic retinopathy"),
        ],
        unacceptable=["DME only affects side vision", "DME is a type of cataract"],
    ),
    dict(
        question="What is an Amsler grid test?",
        reference_answer=(
            "An Amsler grid test tells the doctor if you've lost any central vision. You look at a picture of a grid; "
            "if part of the grid looks wavy or dark, you may have central vision loss (nei_005). It's one of the tests "
            "a doctor may use when checking for macular edema (nei_005)."),
        facts=[
            F("It checks for central vision loss", "nei_005", "This test tells the doctor if you’ve lost any of your central vision"),
            F("Wavy or dark areas on the grid may mean central vision loss", "nei_005",
              "If part of the grid looks wavy or dark, you may have central vision loss"),
        ],
        unacceptable=["The Amsler grid measures eye pressure", "The Amsler grid diagnoses glaucoma"],
    ),
    dict(
        question="What happens during a fluorescein angiogram?",
        reference_answer=(
            "A fluorescein angiogram lets the doctor see pictures of the blood vessels in the retina (nei_005). The "
            "doctor injects a special dye into your arm; the dye travels through the bloodstream to the eye, and a "
            "camera takes photos as it flows through the retinal blood vessels (nei_005). It may be used for conditions "
            "like severe diabetic retinopathy, macular edema, or CRVO (nei_004, nei_019)."),
        facts=[
            F("It shows pictures of the retinal blood vessels", "nei_005",
              "This test lets the doctor see pictures of the blood vessels in your retina"),
            F("Dye is injected into the arm and photographed as it flows through the retina", "nei_005",
              "Your doctor will inject a special dye into your arm"),
            F("It may be used for severe diabetic retinopathy or DME", "nei_004",
              "they may do a test called a fluorescein angiogram"),
        ],
        unacceptable=["The dye is injected directly into the eye", "It is a vision chart test"],
    ),
    dict(
        question="What is optical coherence tomography (OCT)?",
        reference_answer=(
            "OCT is a painless test that uses light waves to take detailed pictures of the retina (nei_017). It lets "
            "the doctor see the back of the eye and can show how much swelling there is, for example in macular edema "
            "or CRVO (nei_005, nei_019). Doctors use it to check for macular holes and to see how severe a macular "
            "pucker is; your doctor may dilate your pupils first (nei_017, nei_018)."),
        facts=[
            F("OCT is painless and uses light waves for detailed retina pictures", "nei_017",
              "This is a painless test that uses light waves to take detailed pictures of your retina"),
            F("It can show how much swelling there is", "nei_005", "This can help your doctor see how much swelling there is"),
            F("It is used to check for macular holes", "nei_017",
              "Your eye doctor will check for a macular hole by doing a test called an optical coherence tomography (OCT)"),
        ],
        unacceptable=["OCT uses X-rays or radiation", "OCT is painful or requires injections"],
    ),
    dict(
        question="I have diabetes and just found out I'm pregnant. Why does that matter for my eyes?",
        reference_answer=(
            "Women with diabetes who become pregnant, or women who develop gestational diabetes, are at high risk for "
            "diabetic retinopathy (nei_004). If you have diabetes and are pregnant, have a comprehensive dilated eye "
            "exam as soon as possible, and ask your doctor whether you'll need additional eye exams during pregnancy "
            "(nei_004). This is general information; your own care plan should come from your doctors."),
        facts=[
            F("Pregnant women with diabetes are at high risk for diabetic retinopathy", "nei_004",
              "Women with diabetes who become pregnant — or women who develop gestational diabetes — are at high risk for getting diabetic retinopathy"),
            F("Get a comprehensive dilated eye exam as soon as possible", "nei_004",
              "If you have diabetes and are pregnant, have a comprehensive dilated eye exam as soon as possible"),
            F("Ask about additional exams during pregnancy", "nei_004",
              "Ask your doctor if you’ll need additional eye exams during your pregnancy"),
        ],
        unacceptable=["Pregnancy lowers the risk of diabetic retinopathy", "Eye exams should wait until after delivery",
                      "Medication advice for pregnancy"],
    ),
    dict(
        question="What is an A1C test and how does it relate to diabetic eye disease?",
        reference_answer=(
            "An A1C test is a lab test that shows your average blood sugar level over the past 3 months; it helps make "
            "sure your diabetes treatment plan is working (nei_004). You can work with your doctor to set a personal "
            "A1C goal, and meeting it can help prevent or manage diabetic retinopathy (nei_004). Diabetic retinopathy "
            "is caused by high blood sugar due to diabetes (nei_004)."),
        facts=[
            F("A1C shows average blood sugar over the past 3 months", "nei_004",
              "This test shows your average blood sugar level over the past 3 months"),
            F("Meeting your A1C goal can help prevent or manage diabetic retinopathy", "nei_004",
              "Meeting your A1C goal can help prevent or manage diabetic retinopathy"),
            F("Diabetic retinopathy is caused by high blood sugar", "nei_004",
              "Diabetic retinopathy is caused by high blood sugar due to diabetes"),
        ],
        unacceptable=["A specific A1C target number for the user", "A1C measures eye pressure"],
    ),
    dict(
        question="What is a vitrectomy?",
        reference_answer=(
            "A vitrectomy is eye surgery in which the doctor makes very small openings in the eye wall and removes most "
            "of the vitreous, the gel-like fluid that fills the eye, with a suction tool (nei_005). It may be used when "
            "other treatments for macular edema haven't worked, for bleeding or scarring from diabetic retinopathy, to "
            "repair a macular hole, or to remove floaters that interfere with daily life (nei_005, nei_004, nei_017, "
            "nei_015)."),
        facts=[
            F("The vitreous gel is removed through small openings with a suction tool", "nei_005",
              "remove most of the vitreous (gel-like fluid that fills your eye) from your eye with a suction tool"),
            F("It may be used for bleeding or scarring from diabetic retinopathy", "nei_004",
              "your eye doctor may recommend a type of surgery called a vitrectomy"),
            F("It is used to fix macular holes", "nei_017",
              "you’ll probably need a type of surgery called vitrectomy to fix the hole and prevent permanent vision loss"),
        ],
        unacceptable=["A vitrectomy replaces the lens", "A vitrectomy is a laser vision correction procedure"],
    ),
    dict(
        question="What are the common symptoms of dry eye?",
        reference_answer=(
            "Dry eye can cause a scratchy feeling like something is in your eye, stinging or burning, red eyes, "
            "sensitivity to light, and blurry vision (nei_006). It happens when the eyes don't make enough tears or the "
            "tears don't work correctly (nei_006). If your eyes feel dry and scratchy, see your eye doctor, who can test "
            "whether your eyes make enough tears (nei_040)."),
        facts=[
            F("Scratchy feeling like something in the eye", "nei_006", "A scratchy feeling, like there’s something in your eye"),
            F("Stinging or burning", "nei_006", "Stinging or burning feelings in your eye"),
            F("Red eyes, light sensitivity, blurry vision", "nei_006", "Sensitivity to light"),
            F("See an eye doctor for testing", "nei_040", "If your eyes feel dry and scratchy, see your eye doctor"),
        ],
        unacceptable=["Dry eye never affects vision", "A diagnosis that the user has dry eye"],
    ),
    dict(
        question="What prescription medicines are used for dry eye?",
        reference_answer=(
            "If dry eye is more serious, an eye doctor may prescribe cyclosporine (Restasis) or lifitegrast (Xiidra); "
            "both are eye drops that can help the eyes make more tears (nei_006). For mild dry eye, the most common "
            "treatment is over-the-counter artificial tears (nei_006). Treatment depends on what's causing the symptoms "
            "(nei_006)."),
        facts=[
            F("Cyclosporine (Restasis) or lifitegrast (Xiidra) may be prescribed for more serious dry eye", "nei_006",
              "your eye doctor may give you a prescription for medicines called cyclosporine (Restasis) or lifitegrast (Xiidra)"),
            F("They help the eyes make more tears", "nei_006",
              "These medicines are both types of eye drops that can help your eyes make more tears"),
            F("Artificial tears are the most common treatment for mild dry eye", "nei_006",
              "The most common treatment for mild dry eye is a type of eye drops called artificial tears"),
        ],
        unacceptable=["Restasis or Xiidra are available over the counter", "Dosing instructions for the user"],
    ),
    dict(
        question="What are punctal plugs for?",
        reference_answer=(
            "Punctal plugs are special plugs an eye doctor may put in the tear ducts, the small holes in the inner "
            "corners of the eyes, if tears are draining too quickly (nei_006). They help keep tears in the eyes and are "
            "one treatment option for dry eye (nei_006)."),
        facts=[
            F("They are placed in tear ducts when tears drain too quickly", "nei_006",
              "If tears are draining too quickly from your eyes, your doctor may suggest putting special plugs (called punctal plugs) in your tear ducts"),
            F("They help keep tears in the eyes", "nei_006", "These plugs can help keep your tears in your eyes"),
        ],
        unacceptable=["Punctal plugs increase tear production", "Punctal plugs are used to treat glaucoma"],
    ),
    dict(
        question="What is Sjögren syndrome and how does it affect the eyes?",
        reference_answer=(
            "Sjögren syndrome is an autoimmune disorder in which the body attacks the glands that make tears and "
            "saliva, causing dry eye, dry mouth, and trouble swallowing (nei_039). Women ages 40 to 50 are at higher "
            "risk, and people with it often have another autoimmune disorder like lupus or rheumatoid arthritis "
            "(nei_039). There's no cure, but you and your doctor can work together to manage symptoms (nei_039)."),
        facts=[
            F("The body attacks the glands that make tears and saliva", "nei_039",
              "your body attacks the glands that make tears and saliva, causing dry eye, dry mouth, and trouble swallowing"),
            F("Women ages 40 to 50 are at higher risk", "nei_039", "women ages 40 to 50 are at higher risk"),
            F("No cure, but symptoms can be managed", "nei_039", "There’s no cure for Sjögren syndrome"),
        ],
        unacceptable=["Sjögren syndrome can be cured", "Sjögren syndrome only affects the eyes",
                      "A diagnosis of Sjögren syndrome for the user"],
    ),
    dict(
        question="Can prescription or over-the-counter medicines lead to dry eye as a side effect?",
        reference_answer=(
            "Yes. Dry eye can be a side effect of some medicines, such as those that treat colds and allergies, "
            "depression, and high blood pressure (nei_039). If a medicine you take for another condition is causing "
            "dry eye, your doctor may suggest trying a different medicine (nei_006)."),
        facts=[
            F("Some medicines for colds/allergies, depression, high blood pressure can cause dry eye", "nei_039",
              "Dry eye can be a side effect of some medicines that treat conditions like colds and allergies, depression, and high blood pressure"),
            F("The doctor may suggest a different medicine", "nei_006",
              "if a medicine you take for another health condition is causing dry eye, your doctor may also suggest that you try a different medicine"),
        ],
        unacceptable=["Stop your medicine if you have dry eye", "Medicines never cause dry eye"],
    ),
    dict(
        question="Is blepharitis contagious?",
        reference_answer=(
            "No. Blepharitis isn't contagious, and it usually doesn't cause lasting damage to the eyes (nei_007). It is "
            "a common condition that makes the eyelids red, swollen, irritated, and itchy, and it can cause crusty "
            "dandruff-like flakes on the eyelashes (nei_007). Most of the time it happens because of too much bacteria "
            "on the eyelids at the base of the eyelashes, or clogged oil glands (nei_007)."),
        facts=[
            F("Blepharitis isn't contagious", "nei_007", "But it isn’t contagious, and it usually doesn’t cause any lasting damage to your eyes"),
            F("It makes eyelids red, swollen, irritated and itchy", "nei_007",
              "Blepharitis is a common eye condition that makes your eyelids red, swollen, irritated, and itchy"),
            F("Usually caused by too much bacteria at the base of the eyelashes", "nei_007",
              "Most of the time, blepharitis happens because you have too much bacteria on your eyelids at the base of your eyelashes"),
        ],
        unacceptable=["Blepharitis is contagious", "Blepharitis usually causes permanent vision loss"],
    ),
    dict(
        question="How should I clean my eyelids if I have blepharitis?",
        reference_answer=(
            "Cleaning the eyelids every day is the main treatment (nei_007). Wash your hands; mix warm water with a "
            "gentle cleanser like baby shampoo; dip a clean, soft cloth or cotton swab in it; press it against your "
            "closed eye for a few minutes to loosen crusts; gently rub where the eyelashes meet the eyelid; rinse with "
            "clean water; and use a new cloth or swab for the other eye (nei_007). Blepharitis usually doesn't go away "
            "completely, so this becomes a long-term routine (nei_007)."),
        facts=[
            F("Use warm water with a gentle cleanser like baby shampoo", "nei_007",
              "Mix warm water with a gentle cleanser, like baby shampoo"),
            F("Press the cloth on the closed eye for a few minutes to loosen crusts", "nei_007",
              "Press the cloth against your closed eye for a few minutes to loosen crusts"),
            F("Use a new cloth or swab for the other eye", "nei_007",
              "Repeat these steps on your other eye using a new cloth or cotton swab"),
            F("A lifelong cleaning routine is needed", "nei_007",
              "You’ll need to follow a routine for cleaning your eyelids for the rest of your life to keep it under control"),
        ],
        unacceptable=["Use the same cloth for both eyes", "One cleaning cures blepharitis permanently"],
    ),
    dict(
        question="What is the difference between a stye and a chalazion?",
        reference_answer=(
            "Both are caused by a blocked oil gland in the eyelid (nei_007). A stye is a red, painful bump on the "
            "eyelid. A chalazion is a hard, painless lump; it often happens when a stye doesn't go away, can make the "
            "eyelid swell and turn red, and will often go away on its own (nei_007). Both can be linked to blepharitis "
            "(nei_007)."),
        facts=[
            F("A stye is a red, painful bump from a blocked oil gland", "nei_007",
              "A stye is a red, painful bump on the eyelid caused by a blocked oil gland"),
            F("A chalazion is a hard, painless lump from a blocked oil gland", "nei_007",
              "A chalazion is a hard, painless lump on the eyelid caused by a blocked oil gland"),
            F("A chalazion will often go away on its own", "nei_007", "A chalazion will often go away on its own"),
        ],
        unacceptable=["A chalazion is painful and a stye is painless", "Styes are caused by viruses",
                      "A diagnosis of the user's bump"],
    ),
    dict(
        question="What causes pink eye?",
        reference_answer=(
            "Most of the time pink eye is caused by a virus or bacteria, and viral pink eye is the most common type "
            "(nei_008). It can also come from allergies, such as pollen or pet fur, or from irritants like chlorinated "
            "pool water, air pollution, or makeup (nei_008). Allergic and irritant pink eye are not contagious "
            "(nei_045). The exact cause can be hard to figure out because the symptoms are usually the same (nei_008)."),
        facts=[
            F("Most pink eye is viral or bacterial; viral is most common", "nei_008",
              "Most of the time, pink eye is caused by a virus or bacteria. Viral pink eye is the most common type"),
            F("Allergies and irritants can cause it", "nei_008",
              "You can also get pink eye from allergies to things like pollen or pet fur"),
            F("Allergic pink eye isn't contagious", "nei_045",
              "This kind of pink eye is not contagious, meaning you can’t pass it to someone else"),
        ],
        unacceptable=["All pink eye is bacterial", "All pink eye is contagious"],
    ),
    dict(
        group="g_antibiotics_viral",
        question="Do antibiotics help viral pink eye?",
        reference_answer=(
            "No. Antibiotics don't help viral pink eye (nei_046). Viral pink eye, the most common type, usually gets "
            "better in 1 to 2 weeks without medicine, though it can sometimes take 3 weeks or more (nei_046). "
            "Antibiotics can speed healing for bacterial pink eye but aren't always needed (nei_046). Note that another "
            "NEI page says pink eye often gets better on its own after 7 to 10 days (nei_008)."),
        facts=[
            F("Antibiotics don't help viral pink eye", "nei_046", "Remember, antibiotics don’t help viral pink eye"),
            F("Viral pink eye usually gets better in 1 to 2 weeks without medicine", "nei_046",
              "Viral pink eye, the most common type, usually gets better in 1 to 2 weeks without medicine"),
            F("Antibiotics can speed bacterial pink eye healing but aren't always needed", "nei_046",
              "Antibiotics can speed up the healing time, but they aren’t always needed"),
        ],
        unacceptable=["Antibiotics cure viral pink eye", "Viral pink eye always needs a prescription"],
    ),
    dict(
        group="g_antibiotics_viral",
        question="Will antibiotic eye drops clear up a viral eye infection like pink eye faster?",
        reference_answer=(
            "No. Antibiotics don't help viral pink eye (nei_046). Viral pink eye usually gets better in 1 to 2 weeks "
            "without medicine, sometimes 3 weeks or more (nei_046). Antibiotics can help bacterial pink eye heal "
            "faster, but they aren't always needed; ask your doctor whether they're right for you (nei_046)."),
        facts=[
            F("Antibiotics don't help viral pink eye", "nei_046", "Remember, antibiotics don’t help viral pink eye"),
            F("Viral pink eye usually gets better in 1 to 2 weeks without medicine", "nei_046",
              "Viral pink eye, the most common type, usually gets better in 1 to 2 weeks without medicine"),
            F("Antibiotics can speed bacterial pink eye healing but aren't always needed", "nei_046",
              "Antibiotics can speed up the healing time, but they aren’t always needed"),
        ],
        unacceptable=["Antibiotics cure viral pink eye", "The user should use leftover antibiotic drops"],
    ),
    dict(
        question="What causes astigmatism?",
        reference_answer=(
            "Astigmatism happens when the cornea or lens has a different shape than normal, which makes light bend "
            "differently as it enters the eye (nei_012). Doctors don't know what causes it and there's no way to "
            "prevent it; some people are born with it, many develop it as children or young adults, and some develop "
            "it after an eye injury or eye surgery (nei_012)."),
        facts=[
            F("The cornea or lens has a different shape than normal", "nei_012",
              "Astigmatism happens when your cornea or lens has a different shape than normal"),
            F("The cause is unknown and it can't be prevented", "nei_012",
              "Doctors don’t know what causes astigmatism, and there’s no way to prevent it"),
            F("It can develop after an eye injury or surgery", "nei_012",
              "Some people may also develop astigmatism after an eye injury or an eye surgery"),
        ],
        unacceptable=["Astigmatism is caused by reading in dim light", "Astigmatism can be prevented"],
    ),
    dict(
        question="Does presbyopia keep getting worse forever?",
        reference_answer=(
            "Presbyopia gets worse over time, but it usually stops getting worse after age 65 (nei_013). It's a normal "
            "part of aging in which the lens gets harder and less flexible, so it stops focusing light correctly on the "
            "retina, and everyone gets it as they get older, usually after age 45 (nei_013)."),
        facts=[
            F("It usually stops getting worse after age 65", "nei_013",
              "Presbyopia gets worse over time, but it usually stops getting worse after age 65"),
            F("The lens becomes harder and less flexible", "nei_013",
              "As you age, the lens in your eye gets harder and less flexible"),
            F("Everyone gets it, usually after age 45", "nei_013",
              "Everyone gets presbyopia as they get older — usually after age 45"),
        ],
        unacceptable=["Presbyopia keeps worsening for life", "Presbyopia can be prevented"],
    ),
    dict(
        question="Can LASIK fix presbyopia?",
        reference_answer=(
            "No. LASIK can't fix presbyopia (nei_049). It works best for adults with nearsightedness, farsightedness, "
            "or astigmatism (nei_049). Since everyone gets presbyopia with age, most people who have LASIK will still "
            "need glasses or contact lenses at some point (nei_049)."),
        facts=[
            F("LASIK can't fix presbyopia", "nei_049", "It can’t fix presbyopia"),
            F("LASIK works best for nearsightedness, farsightedness, astigmatism", "nei_049",
              "It works best for adults with nearsightedness, farsightedness, or astigmatism"),
            F("Most people will still need glasses at some point", "nei_049",
              "most people will still need single vision glasses or contact lenses at some point"),
        ],
        unacceptable=["LASIK cures presbyopia", "After LASIK nobody needs glasses again"],
    ),
    dict(
        question="How long does it take to recover from LASIK?",
        reference_answer=(
            "Right after LASIK your eye may be irritated and your vision blurry, so someone needs to drive you home "
            "(nei_049). You'll be able to see after surgery, but it takes 2 to 3 months for the eye to finish healing, "
            "and vision gets clearer as it heals (nei_049). You may need to wear a protective patch at night for several "
            "nights, and follow-up visits check healing (nei_049)."),
        facts=[
            F("Blurry vision right after surgery; need a ride home", "nei_049",
              "Right after surgery, your eye might be irritated and your vision will be blurry"),
            F("Healing takes 2 to 3 months", "nei_049", "it takes 2 to 3 months for your eye to finish healing"),
            F("A patch may be worn at night for several nights", "nei_049",
              "You may also need to wear a special patch over your eye for several nights"),
        ],
        unacceptable=["Recovery from LASIK takes one day", "You can drive yourself home after LASIK"],
    ),
    dict(
        question="What are some alternatives to LASIK?",
        reference_answer=(
            "Alternatives to LASIK include LASEK (laser epithelial keratomileusis), EpiLasik, phakic intraocular lens "
            "(IOL) implantation, and photorefractive keratectomy (PRK) (nei_049). Glasses and contact lenses are also "
            "ways to correct refractive errors, and glasses are the simplest and safest (nei_009). Your eye doctor can "
            "discuss the risks and benefits (nei_049)."),
        facts=[
            F("Alternatives include LASEK, EpiLasik, phakic IOL, and PRK", "nei_049",
              "Phakic intraocular lens (IOL) implantation"),
            F("Glasses are the simplest and safest correction", "nei_009",
              "Eyeglasses are the simplest and safest way to correct refractive errors"),
        ],
        unacceptable=["LASIK is the only refractive surgery", "A recommendation of a specific surgery for the user"],
    ),
    dict(
        question="At what age does nearsightedness usually start?",
        reference_answer=(
            "Nearsightedness usually starts between ages 6 and 14 and gets worse until the early twenties (nei_010). "
            "Children who spend more time outdoors are less likely to be nearsighted, but experts aren't sure why "
            "(nei_010). Having family members who are nearsighted raises the risk (nei_010)."),
        facts=[
            F("It usually starts between ages 6 and 14 and worsens until the early twenties", "nei_010",
              "Nearsightedness usually starts between ages 6 and 14 and gets worse until your early twenties"),
            F("More outdoor time is linked to less nearsightedness, reason unknown", "nei_010",
              "Children who spend more time outdoors are less likely to be nearsighted, but experts aren’t sure why"),
            F("Family history raises the risk", "nei_010",
              "you’re at higher risk if you have family members who are nearsighted too"),
        ],
        unacceptable=["Nearsightedness usually starts after age 40", "Outdoor time is proven to cure myopia"],
    ),
    dict(
        question="What are the different types of retinal detachment?",
        reference_answer=(
            "There are 3 types: rhegmatogenous, tractional, and exudative (nei_050). Rhegmatogenous, the most common, "
            "happens when a tear or break lets the vitreous get behind the retina; tractional happens when scar tissue "
            "pulls the retina away; exudative happens when fluid builds up behind the retina without a tear (nei_050). "
            "Any type of retinal detachment is a medical emergency (nei_050)."),
        facts=[
            F("The 3 types are rhegmatogenous, tractional, and exudative", "nei_050",
              "There are 3 types of retinal detachment"),
            F("Rhegmatogenous is the most common and involves a tear or break", "nei_050",
              "Rhegmatogenous retinal detachment is the most common type of retinal detachment"),
            F("Exudative involves fluid buildup without tears", "nei_050",
              "Exudative retinal detachment happens when fluid builds up behind your retina, but there aren’t any tears or breaks in your retina"),
            F("Any type is a medical emergency", "nei_050", "Any type of retinal detachment is a medical emergency"),
        ],
        unacceptable=["Some types of retinal detachment are not emergencies", "Exudative detachment always involves a tear"],
    ),
    dict(
        question="What causes tractional retinal detachment?",
        reference_answer=(
            "Tractional retinal detachment happens when scar tissue on the retina pulls it away from the back of the "
            "eye (nei_050). The most common cause is diabetic retinopathy, which damages retinal blood vessels and can "
            "scar the retina (nei_050). People with diabetes should get a comprehensive dilated eye exam at least once "
            "a year (nei_050)."),
        facts=[
            F("Scar tissue pulls the retina away", "nei_050",
              "Tractional retinal detachment happens if scar tissue on your retina pulls your retina away from the back of your eye"),
            F("Diabetic retinopathy is the most common cause", "nei_050",
              "The most common cause of tractional retinal detachment is diabetic retinopathy"),
            F("People with diabetes need a dilated exam at least once a year", "nei_050",
              "If you have diabetes, it’s important to get a comprehensive dilated eye exam at least once a year"),
        ],
        unacceptable=["Tractional detachment is mainly caused by aging", "Tractional detachment is not serious"],
    ),
    dict(
        question="How well does treatment for retinal detachment work?",
        reference_answer=(
            "Treatment for retinal detachment works well, especially if the detachment is caught early (nei_014). Some "
            "people need a second treatment or surgery if the retina detaches again, but treatment is ultimately "
            "successful for about 9 out of 10 people (nei_014). Depending on the type and size, treatment may be laser "
            "surgery, freezing treatment, or other surgery (nei_014)."),
        facts=[
            F("Treatment works well, especially if caught early", "nei_014",
              "Treatment for retinal detachment works well, especially if the detachment is caught early"),
            F("Some need a second treatment", "nei_014", "you may need a second treatment or surgery if your retina detaches again"),
            F("Ultimately successful for about 9 out of 10 people", "nei_014",
              "treatment is ultimately successful for about 9 out of 10 people"),
        ],
        unacceptable=["Treatment always works the first time", "Retinal detachment can't be treated"],
    ),
    dict(
        question="What is posterior vitreous detachment and when does it usually happen?",
        reference_answer=(
            "The vitreous is the gel that fills the eye; it has tiny fibers attached to the retina. As you get older "
            "the fibers pull away from the retina, which is called vitreous detachment, and it usually happens after "
            "age 50 (nei_016). The most common symptom is a sudden increase in floaters, sometimes with flashes in your "
            "side vision (nei_016). Because it can occasionally cause serious problems like a retinal tear, it's "
            "important to see your eye doctor right away if you notice symptoms (nei_016)."),
        facts=[
            F("Vitreous fibers pull away from the retina with age", "nei_016",
              "As you get older, the fibers of your vitreous pull away from the retina"),
            F("It usually happens after age 50", "nei_016", "It usually happens after age 50"),
            F("The most common symptom is a sudden increase in floaters", "nei_016",
              "The most common symptom of vitreous detachment is a sudden increase in floaters"),
            F("See the eye doctor right away if symptoms occur", "nei_016",
              "So if you notice symptoms of vitreous detachment, it’s important to go to your eye doctor right away"),
        ],
        unacceptable=["Vitreous detachment is always harmless and never needs an exam",
                      "Vitreous detachment mostly affects children"],
    ),
    dict(
        question="What is a macular hole?",
        reference_answer=(
            "A macular hole is a rare eye condition in which an opening forms in the macula, the small central area of "
            "the retina, usually after being stretched or pulled (nei_017). It can blur central vision used for driving "
            "or reading; early symptoms are blurry or wavy vision, and later a blind spot can develop (nei_017). Most "
            "macular holes form because of age-related changes, and early treatment with surgery can often restore "
            "vision (nei_017)."),
        facts=[
            F("An opening forms in the macula", "nei_017", "Macular holes happen when an opening forms in the macula"),
            F("It can blur central vision", "nei_017",
              "A macular hole is a rare eye condition that can blur the central vision you use to do everyday tasks like driving or reading"),
            F("Early surgery can often restore vision", "nei_017", "Early treatment with surgery can often restore vision"),
        ],
        unacceptable=["A macular hole is the same as AMD", "A macular hole affects side vision first"],
    ),
    dict(
        question="Why do I have to avoid flying after macular hole surgery?",
        reference_answer=(
            "During macular hole surgery (vitrectomy), the doctor injects a gas bubble into the eye that acts like a "
            "temporary bandage holding the edges of the hole together (nei_017). Until the bubble is completely gone, "
            "you need to avoid flying or getting nitrous oxide (laughing gas), because these can affect the pressure in "
            "the eye (nei_017). You'll also need to limit activity and head movement for a while (nei_017)."),
        facts=[
            F("A gas bubble is injected and acts as a temporary bandage", "nei_017",
              "The bubble is like a temporary bandage that holds the edges of the macular hole together"),
            F("Avoid flying or nitrous oxide until the bubble is gone", "nei_017",
              "You also need to avoid flying or getting nitrous oxide (laughing gas) for any procedures until the bubble is completely gone"),
            F("These can affect eye pressure", "nei_017", "these things can affect the pressure in your eye"),
        ],
        unacceptable=["Flying is fine right after the surgery", "The bubble is permanent"],
    ),
    dict(
        question="What is central retinal vein occlusion (CRVO)?",
        reference_answer=(
            "CRVO is an eye condition that happens when a blood clot blocks the main vein where blood flows out of the "
            "retina; it usually affects only 1 eye (nei_019). Many people have blurry vision, and some have sudden "
            "vision loss (nei_019). There's no cure, but early treatment such as anti-VEGF injections or laser can "
            "lower the chance of vision loss (nei_019)."),
        facts=[
            F("A blood clot blocks the main retinal vein", "nei_019",
              "It happens when a blood clot blocks the main vein where blood flows out of the retina"),
            F("It usually affects only 1 eye", "nei_019", "It usually only affects 1 eye"),
            F("No cure, but treatment can help", "nei_019",
              "There’s no cure for CRVO, but treatment can improve your vision or keep your symptoms from getting worse"),
        ],
        unacceptable=["CRVO is a blocked artery", "CRVO can be cured"],
    ),
    dict(
        question="What are the first symptoms of retinitis pigmentosa?",
        reference_answer=(
            "The most common early symptom of retinitis pigmentosa (RP) is loss of night vision, usually starting in "
            "childhood; parents may notice a child has trouble moving around in the dark or adjusting to dim light "
            "(nei_020). RP also causes loss of side (peripheral) vision, and over time the field of vision can narrow "
            "to tunnel vision (nei_020)."),
        facts=[
            F("Loss of night vision is the most common early symptom", "nei_020",
              "The most common early symptom of RP is loss of night vision"),
            F("It usually starts in childhood", "nei_020", "usually starting in childhood"),
            F("Side vision loss can progress to tunnel vision", "nei_020",
              "Over time, your field of vision narrows until you only have some central vision (also called tunnel vision)"),
        ],
        unacceptable=["RP first causes loss of central vision", "RP can be cured"],
    ),
    dict(
        question="Can vitamin A help retinitis pigmentosa?",
        reference_answer=(
            "Vitamin A may help slow vision loss from the common forms of RP, but taking too much vitamin A can cause "
            "liver problems, so talk with your doctor about the risks and benefits (nei_020). Fish oil and lutein may "
            "also help slow vision loss (nei_020). There's no cure for RP (nei_020)."),
        facts=[
            F("Vitamin A may slow vision loss in common forms of RP", "nei_020",
              "Vitamin A may help slow vision loss from the common forms of RP"),
            F("Too much vitamin A can cause liver problems", "nei_020",
              "But taking too much vitamin A can cause liver problems"),
            F("There's no cure for RP", "nei_020", "There’s no cure for RP"),
        ],
        unacceptable=["Vitamin A cures RP", "A specific vitamin A dose for the user",
                      "Vitamin A is completely safe at any dose"],
    ),
    dict(
        question="What is the uvea?",
        reference_answer=(
            "The uvea is the middle layer of the eye, between the sclera (the white part) and the retina (nei_021). It "
            "has 3 parts: the iris (colored part), the ciliary body (helps the lens focus), and the choroid (connects "
            "the retina to the sclera) (nei_021). Inflammation of the uvea is called uveitis (nei_021)."),
        facts=[
            F("The uvea is the middle layer between sclera and retina", "nei_021",
              "The uvea is the middle layer of the eye between the sclera (white part of the eye) and the retina"),
            F("Its parts are the iris, ciliary body, and choroid", "nei_021", "Ciliary body (the part of the eye that helps the lens focus)"),
        ],
        unacceptable=["The uvea is the clear front layer of the eye", "The uvea includes the lens"],
    ),
    dict(
        question="How is uveitis treated?",
        reference_answer=(
            "Steroid medicines are used to reduce inflammation, ease symptoms, and prevent vision loss (nei_021). They "
            "can be given as prescription eye drops (most common), pills, injections in or around the eye, or a small "
            "implant that releases medicine over time (nei_021). Steroids can increase the risk of cataracts and "
            "glaucoma, so regular eye exams are important (nei_021). The treatment plan depends on which part of the eye "
            "is affected and other health conditions (nei_021)."),
        facts=[
            F("Steroids reduce inflammation and help prevent vision loss", "nei_021",
              "Medicines called steroids can reduce inflammation in your eye"),
            F("Eye drops are the most common form", "nei_021", "Prescription eye drops are the most common treatment"),
            F("Steroids raise the risk of cataracts and glaucoma", "nei_021",
              "Steroids can have side effects and can increase your risk for cataracts and glaucoma"),
        ],
        unacceptable=["Uveitis always goes away without treatment", "Steroids have no side effects",
                      "A specific dosing plan for the user"],
    ),
    dict(
        question="When should a child be screened for amblyopia (lazy eye)?",
        reference_answer=(
            "All kids should get a vision screening at least once between ages 3 and 5 (nei_022). Amblyopia can be hard "
            "to notice, and many parents don't know their child has it until it's found during an eye exam (nei_022). "
            "Early treatment works well and usually prevents long-term vision problems (nei_022)."),
        facts=[
            F("Screening at least once between ages 3 and 5", "nei_022",
              "it’s important for all kids to get a vision screening at least once between ages 3 and 5"),
            F("Many parents don't notice until an eye exam", "nei_022",
              "In many cases, parents don’t know their child has amblyopia until a doctor diagnoses it during an eye exam"),
            F("Early treatment works well", "nei_022",
              "The good news is that early treatment works well and usually prevents long-term vision problems"),
        ],
        unacceptable=["Screening should wait until age 10", "Amblyopia treatment works equally well in adults"],
    ),
    dict(
        question="What is the most common type of color blindness?",
        reference_answer=(
            "The most common type of color vision deficiency makes it hard to tell the difference between red and green "
            "(nei_023). Another type makes blue and yellow look the same, and in rare cases people see no color at all "
            "(nei_023). Most people who have it are born with it because the common types are genetic (nei_023)."),
        facts=[
            F("Red-green is the most common type", "nei_023",
              "The most common type of color vision deficiency makes it hard to tell the difference between red and green"),
            F("Another type confuses blue and yellow", "nei_023", "Another type makes blue and yellow look the same"),
            F("The common types are genetic", "nei_023",
              "This is because the most common types of color vision deficiency are genetic"),
        ],
        unacceptable=["Blue-yellow is the most common type", "Most color blind people see no color at all"],
    ),
    dict(
        question="What does it mean to have low vision?",
        reference_answer=(
            "Low vision is a vision problem that makes it hard to do everyday activities and can't be fixed with "
            "glasses, contact lenses, or other standard treatments like medicine or surgery (nei_024). The most common "
            "causes are AMD, cataracts, diabetic retinopathy, and glaucoma (nei_024). Low vision is usually permanent, "
            "but vision aids and vision rehabilitation can help people make the most of their remaining sight "
            "(nei_024)."),
        facts=[
            F("Low vision can't be fixed with glasses, contacts, or standard treatments", "nei_024",
              "It can’t be fixed with glasses, contact lenses, or other standard treatments like medicine or surgery"),
            F("Most common causes are AMD, cataracts, diabetic retinopathy, glaucoma", "nei_024",
              "Many different eye conditions can cause low vision, but the most common causes are"),
            F("Low vision is usually permanent", "nei_024", "Unfortunately, low vision is usually permanent"),
            F("Vision rehabilitation can help", "nei_024",
              "If your vision loss is getting in the way of everyday activities, ask your eye doctor about vision rehabilitation"),
        ],
        unacceptable=["Low vision is caused by aging itself", "New glasses will fix low vision"],
    ),
    dict(
        question="Why can't I drive myself home after a dilated eye exam?",
        reference_answer=(
            "For a few hours after a dilated eye exam, your vision may be blurry and you may be sensitive to light, so "
            "ask a friend or family member to drive you home (nei_028). Dilation widens the pupil to let more light in "
            "so the doctor can see inside the eye (nei_028). Bringing sunglasses can help with the light sensitivity "
            "(nei_028)."),
        facts=[
            F("Vision may be blurry and light-sensitive for a few hours", "nei_028",
              "For a few hours after a dilated eye exam, your vision may be blurry and you may be sensitive to light"),
            F("Ask someone to drive you home", "nei_028", "Ask a friend or family member to drive you home from your appointment"),
            F("Sunglasses can help", "nei_028", "Sunglasses can help, so bring them if you have them"),
        ],
        unacceptable=["The blurriness lasts for several days", "Dilation damages the eye"],
    ),
]
