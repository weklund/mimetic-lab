# Minimal model v0: Girard's cycle as emergent behaviour

Status: proposed spec, 2026-11-12. Milestone M4-minimal-model (ROADMAP.md). Claims L1 and L2 in `claims/claims.yaml`. Nothing is implemented yet. The headings follow the ODD protocol (Overview, Design concepts, Details) so the description can be checked against the code later.

Epistemic line: this is the lab's own model. A result here upgrades an L claim only, never a G claim. It is a statement about which stated rules are sufficient for which outcomes, not about people.

## 1. Purpose

Find the smallest model in which Girard's four stage cycle emerges from the micro rules rather than being assumed, and measure which rules carry the weight. The four stages, with the claim each stands in for:

1. Desire is borrowed from a model (G1), and near models become rivals while distant ones do not (G2).
2. Shared desire for an object that cannot be shared produces hostility between the rivals (G3).
3. Hostility transmits mimetically and the pull of a target grows with the number already against it, until the group is united against one member (G4).
4. Expelling that member ends the crisis, and the peace lasts for a while (G6). Who the member is (G5) is measured, never chosen.

Existing models assume one of these stages. Black (B1 to B4) seeds hostility by an object rivalry rule it never tests (G3 as input). Paes (O1) programs the victim choice. Sack (S1 to S5) has no hostility at all. The majority and voter readings (O5 to O7) have targets but no objects, no mediator, and no aftermath. This model has all four stages, each with a switch that turns it off or replaces it with a null rule.

## 2. Entities, state variables, and scales

Agents: `i` in `1..N`, on a fixed connected undirected graph `Gamma` with neighbour set `Nb(i)`. Only alive agents count as neighbours.

Objects: `o` in `1..M`, each with capacity 1 (held by at most one agent). Objects are not agents; this differs from Sack, where objects are nodes.

State per agent:

| Variable | Values | Meaning |
|---|---|---|
| `alive_i` | 0 or 1 | In the group. |
| `model_i` | an alive neighbour, or none | The mediator whose desire and hostility `i` copies. |
| `desire_i` | an object, or none | What `i` wants. |
| `holds_i` | an object, or none | What `i` has. Fixed in v0 (objects do not change hands). |
| `target_i` | an alive agent other than `i`, or none | Whom `i` is hostile to. Never `i` itself (switch SELF below). |
| `theta_i` | in (0, 1] | Threshold for rule H2, fixed at initialisation. |
| `recog_i` | 0 or 1 | Recognises transmitted hostility as such (stage R). |

Derived: prestige `p_i` = number of alive agents whose `model` is `i`, plus 1 if `holds_i` is an object. Prestige is deference, as in O12; it is not stored.

Scales: `N` from 4 to 40 for stochastic runs (Black's Table 10 range), all connected graphs with `N <= 6` for exhaustive runs of stage 3 alone. One step is one synchronous update of every stage in order.

## 3. Process overview and scheduling

Each step reads the state at the start of the step and writes at the end (synchronous). Switch SCHED replaces this with random sequential update, because O7 showed that the schedule changes the voter model's outcome; the default is synchronous so that the exhaustive runs are deterministic.

1. Mediation (G1, O12). With probability `mu`, `i` resamples `model_i` from its alive neighbours with probability proportional to `(1 + p_j)^beta`. `beta = 0` is uniform choice (a voter model of mediation); `beta > 0` is prestige bias.
2. Desire (G1). With probability `alpha`, `desire_i := desire_{model_i}` when the model has a desire; otherwise keep.
3. Rivalry (G2, G3). If `desire_i = o`, some `j != i` holds `o`, and `j` is near, then with probability `eta` set `target_i := j`, and with the same probability `target_j := i` (the model becomes the obstacle; the rivals become doubles). Near means `|p_i - p_j| <= tau`. Switch TAU_INF makes every model near, which removes G2.
4. Hostility transmission (G4). Two sub steps, both with switches:
   1. Mediated (4a): with probability `lambda`, `target_i := target_{model_i}` when the model has a target other than `i`. Imitate the model's antagonism.
   2. Conformist (4b): let `n_t(i)` be the number of alive neighbours of `i` whose target is `t`, for `t != i`, and `k_i` the number of alive neighbours. One of:
      1. H1, strict majority (the O5 and O6 rule): adopt `t` if `n_t > k_i / 2`; otherwise keep.
      2. H2, heterogeneous threshold (O8, O9): adopt the unique plurality target `t` if `n_t / k_i >= theta_i`; on a tie, keep. `theta_i` drawn once from `Uniform(theta_min, theta_max)`; `theta_i > 1/2` for all `i` reduces H2 to H1.
      3. H3, conformist or salience (O11; Black's exponent): choose `t` with probability proportional to `c_t^gamma`, where `c_t = n_t`, plus 1 when `t` is the current target. `gamma = 1` is linear copying (Black's B2 says linear transmission never converges in his model); `gamma > 1` amplifies the leader.
   A rule that would select `i` itself keeps the current target (switch SELF, below).
5. Decay. With probability `delta`, `target_i := none`. Hostility fades unless it is renewed. Without decay there is no peace to measure.
6. Expulsion (G4 to G5). Let `share(v)` be the fraction of alive agents other than `v` whose target is `v`. If `share(v) >= u(n_alive)` for some `v`, and at least `cooldown` steps have passed since the last expulsion, set `alive_v := 0` and clear every target that pointed at `v`. `u` is Black's adaptive threshold (all but at most one holdout, capped at 0.95) so that E1 can dock. Targets at agents other than `v` are not cleared: peace, if it comes, must come from stage 5 and from the victim's absence.
7. Recognition (stage R, switch, default off). An agent with `recog_i = 1` skips stage 4: it holds only first hand hostility from stage 3. `recog` spreads like desire: with probability `alpha`, `recog_i := recog_{model_i}`. This is the lab's reading of "sacrifice works only while it is misunderstood" (Girard to Cayley, 2001) and of Chavalarias's agents that imitate rules (O2).

Switch SELF: by default no agent ever targets itself, and the victim keeps its own target to the end. The alternative, SELF = on, lets stage 4 select `i` itself when the rule says so, so the victim can join the accusation. The two conventions carry Girardian content: in the Cayley interviews Girard reads Job's friends as delegates of the mob persuading him to accept that he should be the scapegoat, and says the mechanism wants unanimity "like the Moscow trials of 1937". Both conventions are run; neither is "the" model.

## 4. Design concepts: what is assumed and what must emerge

| Girard claim | Where in the model | Assumed or emergent | Ablation |
|---|---|---|---|
| G1 borrowed desire | stage 2 | The copying rule is assumed (it is the premise). Convergence of desires onto few objects is emergent. | `alpha = 0`. |
| G2 internal vs external mediation | `tau` in stage 3 | Rule assumed. Whether distance matters is emergent. | TAU_INF. |
| G3 rivalry produces hostility | stage 3 | Rule assumed. Whether hostility arises at all is emergent, because it needs desires to converge on capacity 1 objects. Unlike Black, no hostility is seeded. | SEED: skip stages 1 to 3 and seed targets at random (Black mode). |
| G4 snowball to one | stages 4 and 6 | Must emerge. Never assumed. | `lambda = 0`; H1 vs H2 vs H3; `gamma`. |
| G5 who the victim is | measured at stage 6 | Must emerge. Never chosen. | None. |
| G6 peace after expulsion | stages 5 and 6 | Must emerge: no reset of hostility after an expulsion. | RESET: clear all targets after an expulsion (Paes mode), for comparison only. |
| Misrecognition | stage 7 | Switch. | R on or off, initial `recog` fraction. |

Stochasticity: stages 1, 2, 3, 4a, 4b (H3 only), and 5 are stochastic; seeds are fixed and recorded. Stage 4b with H1 or H2 is deterministic, which is what makes E0 exhaustive.

Observation: every per step series the contract's trial schema names (`alive_ids`, `top_targets`, `modal_agreement` as the share of the top target, `eligible_ids` as agents with a target) is recorded, so the same tooling reads these traces. This does not make them official contract trials; the judges are not used here.

## 5. Initialisation

Two starts.

1. Undifferentiated (the crisis Girard describes, each against each). Equal prestige: `model_i` uniform over neighbours, `holds` assigned to `M < N` agents at random (scarcity), `desire_i` uniform over objects, no targets, `recog = 0`.
2. Stage 3 alone, exhaustive (E0): `target` is a derangement (every agent targets a distinct other agent), or any assignment with no self target; no objects, no models.

## 6. Outcome measures

1. Single victim state: some alive `v` such that every other alive agent targets `v`. The victim's own target is free. This is the correct unanimity test when self targeting is forbidden; ordinary agreement (every agent holds the same label) is impossible then, which is the flaw in O6's original delta and in PR #30's classifier.
2. Black's measure, for docking: share of the top target at or above `u(n_alive)` for 10 steps.
3. Time to the first single victim state, and the shape of `share(top)` over time (S curve with a critical mass, or diffusive growth).
4. Victim features at expulsion: prestige rank, degree, number of agents whose model is `v`, whether `v` held a contested object, whether `v` was among the first targeted.
5. Peace: steps after an expulsion until any `share(v)` exceeds a crisis level `c_crisis` again, compared with a control run in which a random agent is removed at the same step. Tension: number of hostile dyads.
6. Fraction of the group consumed, and recurrence intervals, against `N` (the shape of Black's Table 10).
7. Attractor class for deterministic runs: single victim, split fixed point, 2 cycle, longer cycle.

## 7. Experiments

E0. Stage 4b alone, exhaustive. All connected graphs with `N <= 6` (112 at `N = 6`, from the graph atlas), all derangement starts and all no self starts, rules H1 and H2 (H2 with every placement of at most one agent whose threshold is `1 / k_i`, so one neighbour suffices). Report the attractor class counts per rule, per `N`, per start type. Settles L1. Must assert T1 and T2 on every case as a test.

E1. Docking with Black. SEED on (stages 1 to 3 off), H3 with Black's `gamma` grid, Watts Strogatz graph with Black's `k` and `p`, `N = 50`, 600 steps, no expulsion. Expect the qualitative phase boundary (converged count rises across `gamma` about 1.02 to 1.05). This is a docking check with a tolerance to be set before the run, not a contract claim. If it fails, the discrete target representation is the first suspect; a v1 with continuous hostility would then be a different model with its own claims.

E2. Emergence from the undifferentiated start. Full model, `N` in {5, 10, 20, 40}, 20 seeds each. Measure whether hostility arises (G3 emergent), whether and when a single victim state occurs, and victim features. Ablations: `lambda = 0` (no mediated hostility), `gamma = 1` (no amplification), `beta = 0` (no prestige), TAU_INF, SEED. Settles L2.

E3. Aftermath. Continue E2 past the first expulsion. Peace length against the random removal control; recurrence; fraction consumed against `N`.

E4. Recognition. Sweep the initial `recog` fraction from 0 to 1 at the E2 settings that produce single victim states. Measure the peace effect of E3 as a function of recognition.

## 8. Differential predictions

Each is a measurement with rival expectations written down before the run. None is a claim about people until M6 tests it on data.

P1. Victim identity. Girard (G5): not explained by guilt; victims tend to carry signs of marginality. Boehm and Wrangham (O14): the dominant upstart, highest prestige or aggression. DeScioli and Kurzban (O13): the party judged wrong by a shared rule, as against the party with weaker alliances. In the model: correlation of victimhood with prestige rank, degree, and allies, under each rule.

P2. Peace. Hostile dyads after an expulsion fall below the random removal control for longer than decay alone explains (G6), or they do not.

P3. Recognition removes the peace effect (G6's rider on misrecognition), or it does not.

P4. Shape of convergence. Threshold and conformist rules (H2, H3 with `gamma > 1`) give an S curve with a critical mass; linear copying (`gamma = 1`) gives diffusive growth. The shape is observable in timestamped data.

## 9. Formal targets

Both were checked exhaustively on every connected graph with up to 7 vertices on 2026-11-12 (T1 on 39,692 single victim states, T2 on 1,612,125 derangement starts), with PR #30's implementation of the O6 rule. Neither is proved. Issue #15 is the place for the Lean work.

T1. Under H1 with no self targeting and keep own on a tie, a single victim state (every `u != v` targets `v`; `v` targets `w`) is a fixed point if and only if no agent other than `w` has `v` as its only neighbour.
Proof sketch: an agent `u != v` with `k` alive neighbours sees `k - 1` votes for `v` and at most one vote for `w` (from `v`, when `v` is a neighbour). If `v` is not a neighbour, all votes are for `v`. If `v` is a neighbour and `k >= 3`, `v` has a strict majority. If `k = 2`, it is a tie and `u` keeps `v`. If `k = 1` and the neighbour is `v`, `u` adopts `w`, unless `w = u`, which self targeting forbids, so `u` keeps `v`. The victim `v` sees only votes for itself, which it cannot adopt, so it keeps `w`.

T2. Under H1 from a derangement, the only agents that change at the first step are leaves whose neighbour's target is not themselves, and they adopt that target. Corollary: on a graph with minimum degree 2, every derangement is a fixed point.
Proof sketch: in a derangement each agent is targeted by exactly one agent, so the targets of any agent's neighbours are pairwise distinct. A strict majority among `k` distinct values exists only when `k = 1`.
T2 holds for every deterministic rule that depends only on the counts `n_t(i)` and keeps the current target on a tie, H2 included. So from the undifferentiated crisis no count based rule can begin the snowball except at the periphery. Something else must break the symmetry: an existing lead, a leaf, a random tie break, or a mediator. In this model the mediator is stage 4a, which is why L2 asks whether mediation and amplification are jointly load bearing.

Open question, not a target yet: under H2, what is the smallest set of low threshold agents that makes a single victim state reachable from every derangement on a given graph? Watts's vulnerable cluster (O9) is the likely shape of the answer.

## 10. Data sketch for M6

From Claude's memory on 2026-11-12; availability and licensing must be checked before any of this is planned. Before any dataset is opened, the expected sign of each rival in P1 and the expected shape in P4 are recorded on the claim map.

1. Online pile ons (O19). For a sample of targeted accounts: hourly counts of hostile replies and quotes, the target's follower count (prestige), prior ties among participants (allies). Tests P4 (shape of convergence) and P1 (victim features), and P2 if hostility volume after the target leaves or is suspended can be compared with a matched control.
2. The Tolnay and Beck inventory of lynchings in ten Southern states, 1882 to 1930. Victim characteristics and preceding events, for P1's marginality reading; intervals between events in one county, for P2's recurrence.
3. Witch trial records as compiled for Oster (2004) and later work. Timing and victim characteristics.

One dataset, one prediction, one result recorded whatever it is. A second test needs a Lab decision.

## 11. Implementation notes

Python and numpy, no other runtime dependency beyond networkx for the atlas. Deterministic seeds recorded in every output. E0 and the T1, T2 checks are unit tests that fail if a theorem fails on `N <= 6`. Results are written as JSON with the per step series named as in `eval/trial-schema.md`, so `eval/judge/judge_common.load_series` can read them. No judge scores them.

## Change log

- 2026-11-12 v0: first draft, from the PR #30 fidelity review and the T1, T2 checks.
