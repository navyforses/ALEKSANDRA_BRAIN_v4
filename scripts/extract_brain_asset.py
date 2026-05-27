from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

root = Path('/home/ubuntu/ALEKSANDRA_BRAIN_v4')
source = root / 'design_mockups' / 'concept_c_digital_twin_brain_lab.png'
out_dir = root / 'viewer' / 'public' / 'assets'
out_dir.mkdir(parents=True, exist_ok=True)

img = Image.open(source).convert('RGBA')
# Crop the central generated brain visualization from Concept C, excluding side navigation and evidence panels.
# Coordinates are based on the 2560x1440 generated mockup canvas.
crop_box = (610, 210, 1770, 1110)
brain = img.crop(crop_box)

# Add a subtle transparent vignette so the asset blends into the live dark frontend panel.
w, h = brain.size
mask = Image.new('L', (w, h), 0)
pixels = mask.load()
for y in range(h):
    for x in range(w):
        nx = (x - w / 2) / (w / 2)
        ny = (y - h / 2) / (h / 2)
        dist = (nx * nx + ny * ny) ** 0.5
        alpha = int(max(0, min(255, 255 * (1.0 - max(0, dist - 0.72) / 0.28))))
        pixels[x, y] = alpha

# Slightly enhance contrast/saturation; preserve the generated image rather than redrawing it.
brain_rgb = Image.new('RGBA', brain.size, (0, 0, 0, 0))
brain_rgb.alpha_composite(brain)
brain_rgb = ImageEnhance.Contrast(brain_rgb).enhance(1.08)
brain_rgb = ImageEnhance.Color(brain_rgb).enhance(1.05)
brain_rgb.putalpha(mask.filter(ImageFilter.GaussianBlur(2)))

png_path = out_dir / 'generated_digital_twin_brain.png'
webp_path = out_dir / 'generated_digital_twin_brain.webp'
brain_rgb.save(png_path)
brain_rgb.convert('RGB').save(webp_path, 'WEBP', quality=92, method=6)
print(f'created {png_path} {png_path.stat().st_size} bytes')
print(f'created {webp_path} {webp_path.stat().st_size} bytes')
