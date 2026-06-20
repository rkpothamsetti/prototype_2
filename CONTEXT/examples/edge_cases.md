# Edge cases for evaluation

| Scenario | File | Notes |
|----------|------|-------|
| Low light | Generate with `np.full(..., 30)` | CLAHE + low_light_boost applied |
| Motion blur | Apply `cv2.GaussianBlur(img, (15,15), 0)` | quality_score drops |
| Rain | Add noise overlay | Flagged in preprocessing metadata |
| No violations | Empty road image | Should return auto_cleared evidence |

Use `scripts/generate_samples.py` for baseline synthetic images.
