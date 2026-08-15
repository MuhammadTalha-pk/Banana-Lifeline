# Model Evaluation — Banana Leaf Classifier

## Contaminated split vs honest split

Identical recipe, identical hyperparameters, identical quarantine. The only
difference is how images were assigned to train/val/test.

| Split | Accuracy | Macro-F1 | Balanced acc. | Panama recall |
|---|---|---|---|---|
| Original (contaminated) | 0.837 | 0.833 | 0.867 | 0.856 |
| **Clean (group-aware)** | **0.788** | **0.765** | **0.791** | **0.704** |

The contaminated split overstates accuracy by **5.0%**. That gap is the
portion of the original number that was memorisation: 60% of its held-out images
had a near-identical twin in training.

**The clean figures are the real ones.** They are what should appear in the report,
the presentation, and any claim made about field performance.

## Per-class performance (clean split)

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| healthy | 0.757 | 0.906 | 0.825 | 96 |
| panama | 0.610 | 0.704 | 0.654 | 71 |
| sigatoka | 0.881 | 0.763 | 0.818 | 224 |

Panama recall is the number to watch. Fusarium wilt kills the plant and has no
chemical cure, so a missed panama case is the most expensive error the system can
make -- and panama is the smallest class, with the fewest distinct scenes.

## Confusion matrix (clean split)

| truth \ pred | healthy | panama | sigatoka | recall |
|---|---|---|---|---|
| **healthy** | 87 | 2 | 7 | 0.906 |
| **panama** | 5 | 50 | 16 | 0.704 |
| **sigatoka** | 23 | 30 | 171 | 0.763 |

## Scene-level performance

Per-image macro-F1 0.765 against per-scene 0.705. Scene-level treats each photographed plant once,
rather than letting a heavily-photographed plant count many times.

## Background ablation

Every photo comes from one site on one day, so background and lighting barely
vary between classes and a shortcut is readily available. Re-evaluating on a
tight centre crop removes most context:

| Full frame | Centre crop only | Drop |
|---|---|---|
| 0.765 | 0.668 | 0.098 |

The model is largely reading the leaf.

## Calibration and abstention

| Metric | Value |
|---|---|
| Temperature | 2.582 |
| ECE before | 0.1321 |
| ECE after | 0.0873 |
| Abstain threshold | 0.936 |
| Coverage at threshold | 27.6% |
| Target risk | 5% |

Temperature scaling cannot change a prediction -- it divides all logits by one
positive scalar, so the argmax is untouched. It only makes the confidence
number mean what it says, which is what allows a threshold to be trusted.

Below 0.936 confidence the system does not answer; it
asks for a clearer photo or refers the farmer to an extension officer.
