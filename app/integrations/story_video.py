"""Story video generator — assembles slides into animated MP4 with transitions and music.

Uses FFmpeg to create 15s vertical videos (1080x1920) from static slides.
Supports: fade transitions, Ken Burns effect (zoom+pan), text animation.
"""

import asyncio
import os
import subprocess
import tempfile
import uuid

import structlog

logger = structlog.get_logger()

# Video settings
STORY_WIDTH = 1080
STORY_HEIGHT = 1920
FPS = 30


async def generate_story_video(
    slide_images: list[bytes],
    durations: list[float],
    transitions: list[str] | None = None,
    music_path: str | None = None,
    output_format: str = "mp4",
) -> bytes:
    """Generate a story video from slide images.

    Args:
        slide_images: List of image bytes (PNG/JPEG) for each slide
        durations: Duration in seconds for each slide
        transitions: Transition type per slide ("fade", "slide_left", "zoom", "none")
        music_path: Optional path to background music file
        output_format: "mp4" or "webm"

    Returns:
        Video file bytes
    """
    if not slide_images:
        raise ValueError("No slides provided")

    if transitions is None:
        transitions = ["fade"] * len(slide_images)

    # Ensure same length
    while len(transitions) < len(slide_images):
        transitions.append("fade")
    while len(durations) < len(slide_images):
        durations.append(3.0)

    tmpdir = tempfile.mkdtemp(prefix="story_")

    try:
        # 1. Save slide images to temp files
        slide_paths = []
        for i, img_data in enumerate(slide_images):
            path = os.path.join(tmpdir, f"slide_{i:03d}.png")
            with open(path, "wb") as f:
                f.write(img_data)
            slide_paths.append(path)

        # 2. Build FFmpeg filter complex for transitions
        total_duration = sum(durations)
        filter_parts = []
        inputs = []

        for i, (path, dur) in enumerate(zip(slide_paths, durations)):
            # Input each image as a video stream
            inputs.extend(["-loop", "1", "-t", str(dur), "-i", path])

            # Ken Burns effect (slow zoom + slight pan)
            zoom_start = 1.0
            zoom_end = 1.05 + (0.03 * (i % 3))  # Subtle variation per slide
            pan_x = "iw/2-(iw/zoom/2)" if i % 2 == 0 else f"iw/2-(iw/zoom/2)+{10 * (i % 3)}"
            pan_y = "ih/2-(ih/zoom/2)"

            filter_parts.append(
                f"[{i}:v]scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={STORY_WIDTH}:{STORY_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
                f"zoompan=z='min({zoom_start}+({zoom_end}-{zoom_start})*on/(25*{dur}),{zoom_end})':"
                f"x='{pan_x}':y='{pan_y}':"
                f"d={int(dur * FPS)}:s={STORY_WIDTH}x{STORY_HEIGHT}:fps={FPS},"
                f"setpts=PTS-STARTPTS[v{i}]"
            )

        # 3. Add transitions between slides
        if len(slide_paths) == 1:
            final_filter = filter_parts[0].replace(f"[v0]", "[outv]")
        else:
            # Concatenate with xfade transitions
            concat_parts = []
            prev = "v0"

            for i in range(1, len(slide_paths)):
                transition = transitions[i] if i < len(transitions) else "fade"
                offset = sum(durations[:i]) - 0.5  # 0.5s overlap for transition

                if offset < 0:
                    offset = 0

                ffmpeg_transition = {
                    "fade": "fade",
                    "slide_left": "slideleft",
                    "slide_up": "slideup",
                    "zoom": "circleopen",
                    "dissolve": "dissolve",
                    "none": "fade",
                }.get(transition, "fade")

                out = f"xf{i}" if i < len(slide_paths) - 1 else "outv"
                concat_parts.append(
                    f"[{prev}][v{i}]xfade=transition={ffmpeg_transition}:"
                    f"duration=0.5:offset={offset:.2f}[{out}]"
                )
                prev = f"xf{i}"

            final_filter = ";".join(filter_parts + concat_parts)

        # 4. Build FFmpeg command
        output_path = os.path.join(tmpdir, f"story.{output_format}")
        cmd = ["ffmpeg", "-y"]
        cmd.extend(inputs)

        # Add music if provided
        if music_path and os.path.isfile(music_path):
            cmd.extend(["-i", music_path])
            audio_filter = f"[{len(slide_paths)}:a]afade=t=in:st=0:d=1,afade=t=out:st={total_duration - 1.5}:d=1.5,atrim=0:{total_duration}[outa]"
            final_filter += f";{audio_filter}"
            cmd.extend([
                "-filter_complex", final_filter,
                "-map", "[outv]", "-map", "[outa]",
            ])
        else:
            cmd.extend([
                "-filter_complex", final_filter,
                "-map", "[outv]",
            ])

        # Output settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            "-t", str(total_duration),
        ])

        if music_path and os.path.isfile(music_path):
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        cmd.append(output_path)

        # 5. Run FFmpeg
        logger.info("ffmpeg_story_start", slides=len(slide_paths), duration=total_duration)

        proc = await asyncio.to_thread(
            lambda: subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        )

        if proc.returncode != 0:
            logger.error("ffmpeg_story_failed", stderr=proc.stderr[:500])
            # Fallback: simple concatenation without transitions
            return await _simple_concat(slide_paths, durations, music_path, tmpdir)

        with open(output_path, "rb") as f:
            video_bytes = f.read()

        logger.info("ffmpeg_story_done", size_kb=len(video_bytes) // 1024, duration=total_duration)
        return video_bytes

    finally:
        # Cleanup temp files
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


async def _simple_concat(
    slide_paths: list[str],
    durations: list[float],
    music_path: str | None,
    tmpdir: str,
) -> bytes:
    """Fallback: simple slide concatenation without fancy transitions."""
    output_path = os.path.join(tmpdir, "story_simple.mp4")

    # Create concat file
    concat_file = os.path.join(tmpdir, "concat.txt")
    with open(concat_file, "w") as f:
        for path, dur in zip(slide_paths, durations):
            f.write(f"file '{path}'\n")
            f.write(f"duration {dur}\n")
        # Repeat last frame
        f.write(f"file '{slide_paths[-1]}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-vf", f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=decrease,pad={STORY_WIDTH}:{STORY_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
    ]

    if music_path and os.path.isfile(music_path):
        total_dur = sum(durations)
        cmd.extend(["-i", music_path, "-c:a", "aac", "-shortest"])

    cmd.append(output_path)

    proc = await asyncio.to_thread(
        lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    )

    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {proc.stderr[:200]}")

    with open(output_path, "rb") as f:
        return f.read()
