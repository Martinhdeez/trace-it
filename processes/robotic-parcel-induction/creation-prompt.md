Create a complete process named "Robotic parcel induction". Do not add sources,
connectors, subjective review, or outstanding questions.

It decides the next command for a robotic parcel-induction cell from a camera
inspection report.

Use these outcomes:
- HUMAN_REVIEW, priority 4, requires a human.
- PICK, priority 3.
- REORIENT, priority 2.
- WAIT, priority 1 and the default.

Use these required symbols:
- object_detected: boolean. Whether the camera detected a parcel.
- inspection_confidence: number from 0 to 100.
- safe_to_handle: boolean. Whether the parcel is safe for the robot to handle.
- grasp_clear: boolean. Whether the parcel has an unobstructed grasp point.
- orientation_acceptable: boolean. Whether the parcel is already correctly oriented.
- reorientation_possible: boolean. Whether the robot can safely reorient it.

If a value needed by a rule is missing, that rule does not fire. Required missing
values are handled by the platform through escalation.

Keep every numbered condition below as one complete rule. Preserve every AND
inside that rule. Do not split a condition into independent rules.

Add these rules:
1. If an object is detected AND inspection confidence is below 80, HUMAN_REVIEW.
2. If an object is detected AND it is not safe to handle, HUMAN_REVIEW.
3. If an object is detected AND the grasp is not clear, HUMAN_REVIEW.
4. If an object is detected AND inspection confidence is at least 80 AND it is
   safe to handle AND the grasp is clear AND its orientation is acceptable, PICK.
5. If an object is detected AND inspection confidence is at least 80 AND it is
   safe to handle AND the grasp is clear AND its orientation is not acceptable
   AND reorientation is possible, REORIENT.
6. If an object is detected AND its orientation is not acceptable AND
   reorientation is not possible, HUMAN_REVIEW.

Add acceptance examples:
- No object detected, with confidence 95 and all safety fields true: WAIT.
- A detected parcel with confidence 96 that is safe, has a clear grasp, and is
  correctly oriented: PICK.
- A detected parcel with confidence 91 that is safe and has a clear grasp but is
  incorrectly oriented and can be reoriented: REORIENT.
- A detected parcel with confidence 55: HUMAN_REVIEW.
