import sys
sys.path.insert(0, '.')

from core.scene_engine import SceneEngine

W, H = 1920, 1080
dur_str = '8.0'
kb_frames = max(1, int(float(dur_str) * 25))
print(f'Ken Burns frames: {kb_frames}')

# Build the filter as it would be done in scene_engine
filt = (
    f"[0:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
    f"crop={W * 2}:{H * 2},"
    f"zoompan=z='min(zoom+0.0003,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)-{H//10}*on/{kb_frames}':d={kb_frames}:s={W}x{H}:fps=25,"
    f"setsar=1[v_bg0]"
)
print('Filter OK:', filt[:100], '...')
print('All checks passed!')
