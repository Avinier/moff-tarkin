# 🏰 Moff Tarkin

Training models to think like fictional strategic masterminds - not just talk like them.

## What this is

RL-based experiment training base models on TV/movie character decision patterns. The point: capture internal monologue and thought processes, not dialogue mimicry. Want models that can handle business decisions with character-specific reasoning patterns.

**Characters:**
- Tywin Lannister - ruthless long-term thinking
- Chuck McGill - rigid principled reasoning
- General Partagaz - methodical operational control

## Architecture

MoE with learnable routing. Key points:
- Router learns which experts to activate (not hardcoded)
- Multiple experts active per forward pass
- GRPO training with constitutional character constraints
- Character-specific reward functions

```
Input → Learned Router → [Tywin | Chuck | Partagaz] → Weighted Output
                ↑
        (Context determines activation)
```

## Dataset Structure

Decision traces format:
```json
{
  "situation": "Competitor launching price war, 30% share at risk",
  "internal_monologue": "They mistake aggression for strength...",
  "decision": "Maintain premium pricing, let them burn capital",
  "justification": "Market leadership isn't about customer count",
  "character": "tywin_lannister"
}
```

Currently have 80 scenes extracted, need to convert to decision traces.

## Training Details

### Constitutional Specs

Each character has:
- Core behavioral constraints
- Forbidden actions
- Decision patterns

Example for Tywin:
- Must evaluate multi-generational impact
- Cannot make emotionally-driven decisions
- Prioritizes legacy over short-term gains

### Reward Functions

```python
# Tywin rewards
reward = 0.3*strategic_depth + 0.3*power_consolidation +
         0.2*resource_efficiency + 0.2*legacy_building

# Chuck rewards
reward = 0.4*ethical_consistency + 0.3*procedural_correctness +
         0.2*logical_rigor + 0.1*institutional_preservation

# Partagaz rewards
reward = 0.4*operational_precision + 0.3*systemic_control +
         0.2*intelligence_gathering + 0.1*hierarchical_respect
```

## Technical Problems

1. **Router learning**: Need router to discover character-appropriate contexts without manual rules. Planning contrastive pre-training.

2. **Character bleed**: Preventing Tywin's traits from affecting Chuck's responses. Using orthogonal weight init + regularization.

3. **Context length**: Full decision traces exceed typical limits. Hierarchical encoding with attention pooling.

4. **Reward balance**: Character authenticity vs actual business viability. Multi-objective optimization with Pareto frontiers.

## Current Status

| Character | Scenes | Decision Traces |
|-----------|--------|-----------------|
| Tywin | 0 | 0 |
| Chuck | 52 | 0 |
| Partagaz | 8 | 0 |
| Logan Roy | 20 | 0 |

Scene extraction pipeline built, need to:
1. Generate decision traces from scenes
2. Build synthetic situations for augmentation
3. Implement GRPO training loop
4. Design router architecture

## Evaluation

LLM-as-judge with character behavioral specs. Scoring:
- Character authenticity (does it feel like Tywin?)
- Strategic coherence (is reasoning sound?)
- Practical viability (would it work?)
- Internal consistency (thought → decision alignment)

## Stack

- PyTorch + Transformers
- TRL for RLHF
- Base models: Llama-3.1 / Mistral-7B candidates
- SQLite for scenes, Parquet for traces
- A100s for training

## Usage (planned)

```python
advisor = StrategicAdvisor()
response = advisor.get_advice(
    situation="competitor raised $50M, targeting our customers",
    context="B2B SaaS, 60% market share"
)
# Returns: character used, decision, internal reasoning
```

## Open Questions

1. Can learned routers beat manual character→context mapping?
2. Minimum character-specific data for authentic reasoning?
3. Synthetic decision trace quality preservation?
4. Optimal expert activation (sparse vs dense)?

## Why this matters

Most character AI just does surface-level dialogue. This captures how they think through problems. The MoE approach lets the model pick which character's reasoning fits the situation, or blend multiple perspectives.

Not building a chatbot. Building strategic advisors with distinct cognitive patterns.