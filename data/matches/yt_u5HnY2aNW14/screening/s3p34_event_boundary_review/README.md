# S3 P34 source event-boundary review

Open the [click review](http://127.0.0.1:8054/) while its local server is running. It shows the 15 unboxed serve frames 35986–36000 and the 13 unboxed point-ending frames 36138–36150. The images are copied from the hash-bound independent packet. Save one visible-state verdict per frame, then export. Choose **Uncertain** when a ball contact, dead ball or whistle cannot be located from the image. Do not infer an event from the player's pose or from the tracker box alone.

This is a **single-reviewer, previously exposed** source review. It can narrow an event bracket but cannot create a precise contact timestamp where the video does not resolve one. A first definite dead frame after a last definite live frame defines an interval between those frames; it does not prove the ball became dead at the first dead frame. Player floor-state reviews and the staged court transform remain separate evidence.

The frozen interval is intentionally broader than the existing 36001–36138 candidate tracking interval. After export, join its event bounds to that interval and label any source frames outside the reviewed tracker span as not yet player-reviewed. Do not silently call the 138-frame candidate interval a complete serve-to-dead-ball trajectory.

**Completed review:** `completed.json` records the reviewer's clicked serve-contact verdict at 35998 and clicked dead-state verdict at 36138. The other serve statuses and subsequent dead statuses were batch entered from the reviewer's explicit statements, with that provenance in each row. The packet contains no individually reviewed live ending frame before 36138, and `exact_point_end_certified` remains false. See the [event result](../../../../../DELIVERABLES/HONOURS_U5_S3P34_EVENT_BOUNDARY_RESULT.md).

To restart the local review page from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api.s3p34_event_boundary_review:app --host 127.0.0.1 --port 8054
```
