## Expected End-to-End Flow
```
┌─────────────────────────────────────────────────────────────┐
│  USER: Nexus, please have Atlas find viral Brain Power videos and analyze them.
Also get the transcripts for thr top 5.             │
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
│  USER: "Semantica, analyze these videos"                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ## SEMANTICA:                                                 │
│  1. analyze_batch(videos_from_atlas)                        │
│  2. cluster_by_theme()                                      │
│  Returns: Enriched semantic records                         │
│  - primary_theme: "longevity_anti_ageing"                  │
│  - target_persona: {age: "40_60", gender: "mixed"}         │
│  - emotional_tone: ["authority", "hopeful"]                │
│  - brand_safety: {risk_score: 2}                           │
└─────────────────────────────────────────────────────────────┘
If Transcripts NOT Available:

Semantica, take the top 10 videos from the Brain Power search and analyze them.
- Classify each video's primary theme, target persona, emotional tone, and hook pattern based on the available data.

---
