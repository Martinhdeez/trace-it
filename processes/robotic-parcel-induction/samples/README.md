# Robotic parcel induction samples

First, paste [`creation-prompt.md`](../creation-prompt.md) into the frontend chat.
Then upload these PDFs to the `Robotic parcel induction` process.

| File | Expected command |
| --- | --- |
| `inspection-wait.pdf` | `WAIT` |
| `inspection-pick.pdf` | `PICK` |
| `inspection-reorient.pdf` | `REORIENT` |
| `inspection-human-review.pdf` | `HUMAN_REVIEW` |

The `.page` files are the text sources used to regenerate the PDFs with `mutool create`.
