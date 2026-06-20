# Test media (downloaded via Tavily search)

Free-licensed samples for Nigha AI helmet / traffic violation testing.

## Videos (`videos/`)

| File | Source | Notes |
|------|--------|-------|
| `indian_highway_motorbikes.mp4` | [Pexels #30104783](https://www.pexels.com/video/busy-indian-highway-with-trucks-and-motorbikes-30104783/) | Indian highway, trucks + bikes (~125 MB) |
| `indian_city_street_traffic.mp4` | [Pexels #35262213](https://www.pexels.com/video/vibrant-indian-city-street-view-with-traffic-35262213/) | Busy Indian city street (~27 MB) |
| `india_auto_rickshaw_traffic.mp4` | [Pexels #35492067](https://www.pexels.com/video/auto-rickshaw-bikes-busy-road-cars-35492067/) | Auto-rickshaws, bikes, cars (~28 MB) |
| `jakarta_traffic_motorcycles.mp4` | [Pexels #14552312](https://www.pexels.com/video/free-stockfootage-jakarta-traffic-14552312/) | Dense motorcycle traffic (~12 MB) |
| `helmet_violation_demo.mp4` | [GitHub YOLO helmet demo](https://github.com/ThanhSan97/Helmet-Violation-Detection-Using-YOLO-and-VGG16) | Research demo clip (~25 MB) |

## Images (`images/`)

| File | Source | Notes |
|------|--------|-------|
| `india_busy_road.jpg` | Pexels frame (35492067) | Indian road scene |
| `indian_city_traffic_frame.jpg` | Pexels frame (35262213) | City traffic still |
| `indian_highway_frame.jpg` | Pexels frame (30104783) | Highway still |
| `helmet_detection_sample.png` | GitHub helmet-detection project | Sample detection UI |
| `no_helmet_violation_frame.jpg` | MehmetCokol/helmet-violation-detection | Annotated no-helmet frame |
| `helmet_compliant_frame.jpg` | MehmetCokol/helmet-violation-detection | Annotated helmet frame |
| `indian_riders_research_sample.jpg` | PMC open-access paper | Indian two-wheeler riders |

## Quick test commands

```powershell
# Single video demo (annotated MP4 output)
.\.venv\Scripts\python.exe scripts\demo_video.py data\test_media\videos\indian_city_street_traffic.mp4

# Batch images
.\.venv\Scripts\python.exe scripts\batch_process.py data\test_media\images

# Batch videos
.\.venv\Scripts\python.exe scripts\batch_process.py data\test_media\videos --videos
```

Or upload any file via the dashboard at http://127.0.0.1:8001
