## Expected End-to-End Flow
```
┌─────────────────────────────────────────────────────────────┐
│  USER: Nexus, please have Atlas find viral Brain Power videos and analyze them.
Also get the transcripts if available.           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  NEXUS: Routes to Atlas                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ATLAS:                                                     │
│  1. search_youtube_videos("NMN supplements")                │
│  2. get_video_details() → metrics                          │
│  3. get_batch_transcripts() → transcripts ← NEW            │
│  4. calculate_priority_scores() → ranked list              │
│  Returns: 10 videos with full data + transcripts           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  USER: "Semantica, analyze the videos pulled by Atlas. I hope you will have the transcripts.
If transcripts are not available, classify each video's primary theme, target persona, emotional tone, and hook pattern based on the available data. Provide a very detailed analysis.                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SEMANTICA:                                                 │
│  1. analyze_batch(videos_from_atlas)                        │
│  2. cluster_by_theme()                                      │
│  Returns: Enriched semantic records                         │
│  - primary_theme: "longevity_anti_ageing"                  │
│  - target_persona: {age: "40_60", gender: "mixed"}         │
│  - emotional_tone: ["authority", "hopeful"]                │
│  - brand_safety: {risk_score: 2}                           │
└─────────────────────────────────────────────────────────────┘
If Transcripts NOT Available:

Semantica, 


Test Scout - eBay market intel

   Scout, search eBay for "nootropics brain supplements" and show me the top sellers

---🧪 Test Prompts for Composable Workflow System

Test 1: Full Monetization Pipeline
Run monetization pipeline for Brain Power
Expected:

📍 Phase 1/4: ATLAS executes, finds viral videos
✅ Presents results table
👉 Checkpoints: "Continue to Phase 2 (Semantica)?"

Then say: continue

Test 2: Trend Discovery Pipeline
Start trend discovery for longevity supplements
Expected:

📍 Phase 1/3: PULSE executes, finds Google Trends
✅ Presents trending topics
👉 Checkpoints: "Continue to Phase 2 (Sage)?"


Test 3: Content Research (No Products)
Run content research pipeline for NMN supplements
Expected:

Sequence: Atlas → Semantica → Sage (skips Sara)


Test 4: Competitor Intelligence
Run competitor analysis for nootropics
Expected:

📍 Phase 1/3: SCOUT searches eBay
Then Sara, then Sage


Test 5: Product-First Pipeline
Start product first workflow for Mental category
Expected:

📍 Phase 1/3: SARA gets Fuxion products first
Then Semantica extracts themes
Then Atlas finds matching content


Test 6: Custom Entry Point (Direct Agent)
Atlas, find viral videos about intermittent fasting
Expected:

Goes directly to Atlas (no pipeline)
After results, offers next steps: Semantica, Sara, or Sage


Test 7: Mid-Workflow Commands
Start with:
Run monetization pipeline for anti-aging
After Phase 1 completes, test these commands:
CommandExpected ResultcontinueProceeds to Phase 2 (Semantica)skip to SaraJumps to Phase 3 (Sara)skip SaraRemoves Sara from sequencestatusShows workflow statestopEnds workflow

Test 8: Workflow Status Check
Run monetization pipeline for brain health
After Phase 1, say:
status
Expected:
📊 Current Workflow Status

- Type: Monetization Pipeline
- Topic: brain health
- Progress: Phase 1/4
- Sequence: Atlas ✅ → Semantica ⏳ → Sara ⏳ → Sage ⏳

Completed Results:
- Atlas: 20 viral videos found

👉 Say 'continue' for Phase 2 (Semantica)

Test 9: Adjust/Retry Phase
Run monetization pipeline for sleep optimization
After Phase 1, say:
adjust - focus only on videos with over 100K views
Expected: Re-runs Atlas with the new filter criteria

Test 10: Custom Sequence
Run Pulse, then Atlas, then Semantica for the top trending topic
Expected: Executes custom 3-phase workflow with checkpoints

🎯 Quick Validation Checklist
TestPass Criteria✅ Triggers workflowRecognizes "monetization pipeline" trigger✅ Executes Phase 1Actually calls Atlas tools, not just describes✅ Shows resultsPresents formatted table of findings✅ CheckpointsPauses and asks before Phase 2✅ Continues"continue" triggers Phase 2✅ Skip works"skip to Sara" jumps phases✅ Status works"status" shows workflow state✅ Stop works"stop" ends workflow cleanly
